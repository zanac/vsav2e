/*
 * psxrun: a minimal, scriptable libretro frontend used to inspect the PlayStation
 * Darkstalkers 3 while it runs (for the vsav2e texts and graphics).
 *
 * It loads a libretro core (PCSX-ReARMed, which has a built-in HLE BIOS), boots a disc
 * image and runs a fixed number of frames with no window and no sound. What happens is
 * driven by environment variables, so a shell script can replay the same session:
 *
 *   PRESS  "frame:button[:hold];..."  press a pad button at a frame (hold, default 4 frames)
 *                                     buttons: b y select start up down left right a x l r
 *                                     (libretro names: b = cross, a = circle, y = square,
 *                                      x = triangle)
 *   SHOTS  "frame frame ..."          save the picture of those frames as OUTDIR/fNNNNNN.ppm
 *   DUMPS  "frame frame ..."          save main RAM (2 MB) as OUTDIR/ram_NNNNNN.bin
 *   VDUMPS "frame frame ..."          save the GPU VRAM (1024 x 512 16-bit words) as
 *                                     OUTDIR/vram_NNNNNN.bin (needs a core that hands it
 *                                     out as RETRO_MEMORY_VIDEO_RAM, see docs/psx.md)
 *   POKES  "first-last:address:value;..."  write a byte of main RAM on every frame of the
 *                                     range (address is a RAM offset, 0..0x1fffff, in hex)
 *   STATE_SAVE "frame:file"           save a state at that frame
 *   STATE_LOAD "file"                 load a state before the first frame
 *
 * usage: psxrun core.so disc.cue frames outdir
 */
#include <dlfcn.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* the few libretro definitions we need (from libretro.h) */
#define RETRO_ENVIRONMENT_GET_CAN_DUPE          3
#define RETRO_ENVIRONMENT_GET_SYSTEM_DIRECTORY  9
#define RETRO_ENVIRONMENT_SET_PIXEL_FORMAT     10
#define RETRO_ENVIRONMENT_GET_VARIABLE         15
#define RETRO_ENVIRONMENT_GET_LOG_INTERFACE    27
#define RETRO_ENVIRONMENT_GET_SAVE_DIRECTORY   31
#define RETRO_MEMORY_SYSTEM_RAM                 2
#define RETRO_MEMORY_VIDEO_RAM                  3
#define PSX_VRAM_BYTES                    0x100000
#define PIXEL_FORMAT_0RGB1555 0
#define PIXEL_FORMAT_XRGB8888 1
#define PIXEL_FORMAT_RGB565   2

struct retro_game_info { const char *path; const void *data; size_t size; const char *meta; };
struct retro_variable { const char *key; const char *value; };
struct retro_log_callback { void (*log)(int level, const char *fmt, ...); };

/* ---- the session script ------------------------------------------------------------ */

#define MAX_EVENTS 1024

struct button_press { int frame, button, hold; };
struct ram_poke { int first_frame, last_frame; uint32_t address; uint8_t value; };

static struct button_press presses[MAX_EVENTS]; static int press_count;
static int shot_frames[MAX_EVENTS];             static int shot_count;
static int dump_frames[MAX_EVENTS];             static int dump_count;
static int vram_dump_frames[MAX_EVENTS];        static int vram_dump_count;
static struct ram_poke pokes[MAX_EVENTS];       static int poke_count;

static const char *output_directory;
static int current_frame;
static int pixel_format = PIXEL_FORMAT_0RGB1555;

/* libretro joypad button ids in the order of the names accepted in PRESS */
static const char *button_names[] = {
	"b", "y", "select", "start", "up", "down", "left", "right", "a", "x", "l", "r", NULL
};

static int button_id(const char *name)
{
	for (int id = 0; button_names[id]; id++)
		if (!strcmp(button_names[id], name))
			return id;
	fprintf(stderr, "unknown button '%s'\n", name);
	exit(1);
}

static bool frame_listed(const int *frames, int count, int frame)
{
	for (int i = 0; i < count; i++)
		if (frames[i] == frame)
			return true;
	return false;
}

static void parse_frame_list(const char *text, int *frames, int *count)
{
	char *copy = strdup(text ? text : "");
	for (char *item = strtok(copy, " ,"); item && *count < MAX_EVENTS; item = strtok(NULL, " ,"))
		frames[(*count)++] = atoi(item);
	free(copy);
}

static void parse_presses(const char *text)
{
	char *copy = strdup(text ? text : "");
	for (char *item = strtok(copy, ";"); item && press_count < MAX_EVENTS; item = strtok(NULL, ";")) {
		char name[32] = ""; int frame = 0, hold = 4;
		if (sscanf(item, "%d:%31[a-z]:%d", &frame, name, &hold) >= 2)
			presses[press_count++] = (struct button_press){ frame, button_id(name), hold };
	}
	free(copy);
}

static void parse_pokes(const char *text)
{
	char *copy = strdup(text ? text : "");
	for (char *item = strtok(copy, ";"); item && poke_count < MAX_EVENTS; item = strtok(NULL, ";")) {
		int first, last; unsigned address, value;
		if (sscanf(item, "%d-%d:%x:%x", &first, &last, &address, &value) == 4)
			pokes[poke_count++] = (struct ram_poke){ first, last, address, (uint8_t)value };
	}
	free(copy);
}

/* ---- callbacks the core calls ------------------------------------------------------ */

static void log_message(int level, const char *format, ...)
{
	if (level < 2) return;                  /* warnings and errors only */
	va_list args; va_start(args, format); vfprintf(stderr, format, args); va_end(args);
}

static bool environment(unsigned command, void *data)
{
	static const char *system_directory = ".";
	switch (command) {
	case RETRO_ENVIRONMENT_GET_SYSTEM_DIRECTORY:
	case RETRO_ENVIRONMENT_GET_SAVE_DIRECTORY:
		*(const char **)data = system_directory; return true;
	case RETRO_ENVIRONMENT_SET_PIXEL_FORMAT:
		pixel_format = *(int *)data; return true;
	case RETRO_ENVIRONMENT_GET_LOG_INTERFACE:
		((struct retro_log_callback *)data)->log = log_message; return true;
	case RETRO_ENVIRONMENT_GET_CAN_DUPE:
		*(bool *)data = true; return true;
	case RETRO_ENVIRONMENT_GET_VARIABLE: {
		/* core options: keep the defaults, except the BIOS (built-in HLE) and the
		   recompiler (the interpreter is slower but does not mind RAM pokes) */
		struct retro_variable *variable = data;
		if (!strcmp(variable->key, "pcsx_rearmed_bios")) { variable->value = "HLE"; return true; }
		if (!strcmp(variable->key, "pcsx_rearmed_drc")) {
			variable->value = getenv("DYNAREC") ? "enabled" : "disabled";
			return true;
		}
		variable->value = NULL; return false;
	}
	}
	return false;
}

/* the last picture the core produced, as 8-bit RGB (the core may send no new picture on
   a frame when nothing changed, so a shot always uses the latest one) */
static uint8_t *last_picture;
static unsigned last_width, last_height;

static void video_refresh(const void *pixels, unsigned width, unsigned height, size_t pitch)
{
	if (!pixels)
		return;                             /* same picture as before */
	if (width != last_width || height != last_height) {
		free(last_picture);
		last_picture = malloc(width * height * 3);
		last_width = width; last_height = height;
	}
	uint8_t *out = last_picture;
	for (unsigned y = 0; y < height; y++) {
		const uint8_t *row = (const uint8_t *)pixels + y * pitch;
		for (unsigned x = 0; x < width; x++, out += 3) {
			if (pixel_format == PIXEL_FORMAT_XRGB8888) {
				uint32_t p = ((const uint32_t *)row)[x];
				out[0] = p >> 16; out[1] = p >> 8; out[2] = p;
			} else {
				uint16_t p = ((const uint16_t *)row)[x];
				if (pixel_format == PIXEL_FORMAT_RGB565) {
					out[0] = (p >> 11) << 3; out[1] = ((p >> 5) & 63) << 2; out[2] = (p & 31) << 3;
				} else {
					out[0] = ((p >> 10) & 31) << 3; out[1] = ((p >> 5) & 31) << 3; out[2] = (p & 31) << 3;
				}
			}
		}
	}
}

/* writes the latest picture as OUTDIR/fNNNNNN.ppm */
static void save_picture(void)
{
	if (!last_picture)
		return;
	char path[1024];
	snprintf(path, sizeof path, "%s/f%06d.ppm", output_directory, current_frame);
	FILE *file = fopen(path, "wb");
	fprintf(file, "P6 %u %u 255\n", last_width, last_height);
	fwrite(last_picture, 1, last_width * last_height * 3, file);
	fclose(file);
}

static void audio_sample(int16_t left, int16_t right) { (void)left; (void)right; }
static size_t audio_batch(const int16_t *samples, size_t frames) { (void)samples; return frames; }
static void input_poll(void) {}

/* player 1's pad: pressed while a PRESS event covers the current frame */
static int16_t input_state(unsigned port, unsigned device, unsigned index, unsigned id)
{
	(void)device; (void)index;
	if (port != 0) return 0;
	for (int i = 0; i < press_count; i++)
		if (presses[i].button == (int)id && current_frame >= presses[i].frame
		    && current_frame < presses[i].frame + presses[i].hold)
			return 1;
	return 0;
}

/* ---- main ---------------------------------------------------------------------------- */

#define LOAD(symbol) symbol##_fn = dlsym(core, #symbol); if (!symbol##_fn) { fprintf(stderr, "%s missing\n", #symbol); return 1; }

int main(int argc, char **argv)
{
	if (argc < 5) {
		fprintf(stderr, "usage: %s core.so disc.cue frames outdir\n", argv[0]);
		return 1;
	}
	void *core = dlopen(argv[1], RTLD_NOW);
	if (!core) { fprintf(stderr, "%s\n", dlerror()); return 1; }

	void (*retro_set_environment_fn)(void *); void (*retro_set_video_refresh_fn)(void *);
	void (*retro_set_audio_sample_fn)(void *); void (*retro_set_audio_sample_batch_fn)(void *);
	void (*retro_set_input_poll_fn)(void *); void (*retro_set_input_state_fn)(void *);
	void (*retro_init_fn)(void); bool (*retro_load_game_fn)(const struct retro_game_info *);
	void (*retro_run_fn)(void); void *(*retro_get_memory_data_fn)(unsigned);
	size_t (*retro_serialize_size_fn)(void); bool (*retro_serialize_fn)(void *, size_t);
	bool (*retro_unserialize_fn)(const void *, size_t);
	LOAD(retro_set_environment) LOAD(retro_set_video_refresh) LOAD(retro_set_audio_sample)
	LOAD(retro_set_audio_sample_batch) LOAD(retro_set_input_poll) LOAD(retro_set_input_state)
	LOAD(retro_init) LOAD(retro_load_game) LOAD(retro_run) LOAD(retro_get_memory_data)
	LOAD(retro_serialize_size) LOAD(retro_serialize) LOAD(retro_unserialize)

	retro_set_environment_fn(environment);
	retro_set_video_refresh_fn(video_refresh);
	retro_set_audio_sample_fn(audio_sample);
	retro_set_audio_sample_batch_fn(audio_batch);
	retro_set_input_poll_fn(input_poll);
	retro_set_input_state_fn(input_state);
	retro_init_fn();

	struct retro_game_info game = { argv[2], NULL, 0, NULL };
	if (!retro_load_game_fn(&game)) { fprintf(stderr, "cannot load %s\n", argv[2]); return 1; }

	int frame_total = atoi(argv[3]);
	output_directory = argv[4];
	parse_presses(getenv("PRESS"));
	parse_frame_list(getenv("SHOTS"), shot_frames, &shot_count);
	parse_frame_list(getenv("DUMPS"), dump_frames, &dump_count);
	parse_frame_list(getenv("VDUMPS"), vram_dump_frames, &vram_dump_count);
	parse_pokes(getenv("POKES"));

	/* optional save states */
	const char *state_to_load = getenv("STATE_LOAD");
	if (state_to_load) {
		retro_run_fn();                     /* the core must have run once before a state can be loaded */
		FILE *file = fopen(state_to_load, "rb");
		size_t size = retro_serialize_size_fn(); void *buffer = malloc(size);
		size_t got = fread(buffer, 1, size, file); fclose(file);
		if (!retro_unserialize_fn(buffer, got)) fprintf(stderr, "state not loaded\n");
		free(buffer);
	}
	int state_save_frame = -1; char state_save_path[1024] = "";
	if (getenv("STATE_SAVE"))
		sscanf(getenv("STATE_SAVE"), "%d:%1023s", &state_save_frame, state_save_path);

	uint8_t *ram = retro_get_memory_data_fn(RETRO_MEMORY_SYSTEM_RAM);
	for (current_frame = 0; current_frame < frame_total; current_frame++) {
		for (int i = 0; i < poke_count; i++)
			if (current_frame >= pokes[i].first_frame && current_frame <= pokes[i].last_frame)
				ram[pokes[i].address & 0x1fffff] = pokes[i].value;
		retro_run_fn();
		if (frame_listed(shot_frames, shot_count, current_frame))
			save_picture();
		if (frame_listed(dump_frames, dump_count, current_frame)) {
			char path[1024];
			snprintf(path, sizeof path, "%s/ram_%06d.bin", output_directory, current_frame);
			FILE *file = fopen(path, "wb"); fwrite(ram, 1, 0x200000, file); fclose(file);
		}
		if (frame_listed(vram_dump_frames, vram_dump_count, current_frame)) {
			const uint8_t *vram = retro_get_memory_data_fn(RETRO_MEMORY_VIDEO_RAM);
			if (vram) {
				char path[1024];
				snprintf(path, sizeof path, "%s/vram_%06d.bin", output_directory, current_frame);
				FILE *file = fopen(path, "wb"); fwrite(vram, 1, PSX_VRAM_BYTES, file); fclose(file);
			} else
				fprintf(stderr, "the core does not hand out its VRAM\n");
		}
		if (current_frame == state_save_frame) {
			size_t size = retro_serialize_size_fn(); void *buffer = malloc(size);
			retro_serialize_fn(buffer, size);
			FILE *file = fopen(state_save_path, "wb"); fwrite(buffer, 1, size, file); fclose(file);
			free(buffer);
		}
	}
	return 0;
}

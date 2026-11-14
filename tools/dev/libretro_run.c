/* libretro_run.c - runs a game in a libretro core with no display, for tests.

   libretro_run CORE.so GAME.zip FRAMES

   Everything else comes from the environment, like tools/trace/drive.lua for MAME:

   SYSTEM_DIR   directory the core may write to (default: the current one)
   OUT          prefix of the screenshots (default "shot_"): OUT<frame>.ppm
   SHOTS        frames to save, "950 1700 2400"
   AUDIO        file the sound is saved to: 16-bit stereo, as the core gives it, with
                no header (the sample rate is printed at the end)
   PRESS        "frame:button;frame:button": the button of player 1 is held 4 frames.
                Buttons: coin start up down left right b1 b2 b3 b4 b5 b6; with "p2." in
                front ("1100:p2.start") the button is player 2's
   MASH         from this frame on, random directions and buttons for player 1
   SEED         seed of MASH (default 1)
   POKES        "first-last:address:value;..." (hexadecimal address and value): the byte
                is written to the 68000 memory on every frame from first to last
   DUMPS        frames at which memory is saved: OUT<frame>_sprites.bin (the sprite list,
                0x708000-0x709fff), OUT<frame>_palettes.bin (0x90c000-0x90c3ff) and
                OUT<frame>_ram.bin (0xff8000-0xffbfff), OUT<frame>_wram.bin (all the
                work RAM, 0xff0000-0xffffff)
   AUTOWIN      from this frame on, player 1 keeps full vitality and player 2 has none
                (Vampire Savior 2 RAM)

   POKES, DUMPS and AUTOWIN need a core built with
   tools/dev/mame2003plus-dev-memory.patch, which adds retro_dev_write8() and
   retro_dev_read8(); without it they are refused.

   Build: cc -O2 -o libretro_run libretro_run.c -ldl */
#include <dlfcn.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* the few parts of libretro.h this program uses */
#define RETRO_ENVIRONMENT_GET_CAN_DUPE 3
#define RETRO_ENVIRONMENT_GET_SYSTEM_DIRECTORY 9
#define RETRO_ENVIRONMENT_SET_PIXEL_FORMAT 10
#define RETRO_ENVIRONMENT_GET_VARIABLE 15
#define RETRO_ENVIRONMENT_GET_LOG_INTERFACE 27
#define RETRO_ENVIRONMENT_GET_SAVE_DIRECTORY 31
#define RETRO_PIXEL_FORMAT_XRGB8888 1
#define RETRO_PIXEL_FORMAT_RGB565 2
#define RETRO_DEVICE_JOYPAD 1
#define RETRO_DEVICE_ID_JOYPAD_B 0
#define RETRO_DEVICE_ID_JOYPAD_Y 1
#define RETRO_DEVICE_ID_JOYPAD_SELECT 2
#define RETRO_DEVICE_ID_JOYPAD_START 3
#define RETRO_DEVICE_ID_JOYPAD_UP 4
#define RETRO_DEVICE_ID_JOYPAD_DOWN 5
#define RETRO_DEVICE_ID_JOYPAD_LEFT 6
#define RETRO_DEVICE_ID_JOYPAD_RIGHT 7
#define RETRO_DEVICE_ID_JOYPAD_A 8
#define RETRO_DEVICE_ID_JOYPAD_X 9
#define RETRO_DEVICE_ID_JOYPAD_L 10
#define RETRO_DEVICE_ID_JOYPAD_R 11
#define JOYPAD_BUTTONS 16

struct retro_game_info { const char *path; const void *data; size_t size; const char *meta; };
struct retro_variable { const char *key; const char *value; };
struct retro_log_callback { void (*log)(int level, const char *format, ...); };

/* Vampire Savior 2 RAM (docs/analysis.md) */
#define PLAYER_1_VITALITY 0xff8450
#define PLAYER_2_VITALITY 0xff8850
#define FULL_VITALITY 288

/* button names of PRESS; the six attack buttons follow the default ("classic") layout
   of mame2003-plus: B, A, Y, X, L, R are buttons 1 to 6 */
static const struct { const char *name; int joypad_id; } button_names[] = {
    { "coin", RETRO_DEVICE_ID_JOYPAD_SELECT }, { "start", RETRO_DEVICE_ID_JOYPAD_START },
    { "up", RETRO_DEVICE_ID_JOYPAD_UP }, { "down", RETRO_DEVICE_ID_JOYPAD_DOWN },
    { "left", RETRO_DEVICE_ID_JOYPAD_LEFT }, { "right", RETRO_DEVICE_ID_JOYPAD_RIGHT },
    { "b1", RETRO_DEVICE_ID_JOYPAD_B }, { "b2", RETRO_DEVICE_ID_JOYPAD_A },
    { "b3", RETRO_DEVICE_ID_JOYPAD_Y }, { "b4", RETRO_DEVICE_ID_JOYPAD_X },
    { "b5", RETRO_DEVICE_ID_JOYPAD_L }, { "b6", RETRO_DEVICE_ID_JOYPAD_R },
};
#define BUTTON_NAME_COUNT ((int)(sizeof button_names / sizeof button_names[0]))
#define PRESS_FRAMES 4

struct press { int frame; unsigned port; int joypad_id; };
struct poke { int first_frame, last_frame; unsigned address, value; };

#define MAXIMUM_ITEMS 256
static struct press presses[MAXIMUM_ITEMS];
static int press_count;
static struct poke pokes[MAXIMUM_ITEMS];
static int poke_count;
static int shot_frames[MAXIMUM_ITEMS];
static int shot_count;
static int dump_frames[MAXIMUM_ITEMS];
static int dump_count;
static int mash_from_frame = -1;
static int autowin_from_frame = -1;
static bool mashed_buttons[JOYPAD_BUTTONS];

static int current_frame;
static int pixel_format;
static const char *system_directory = ".";
static const char *shot_prefix = "shot_";

static void core_log(int level, const char *format, ...)
{
    va_list arguments;

    if (level < 2 && !getenv("VERBOSE"))
        return;
    va_start(arguments, format);
    vfprintf(stderr, format, arguments);
    va_end(arguments);
}

static bool environment(unsigned command, void *data)
{
    switch (command) {
    case RETRO_ENVIRONMENT_GET_SYSTEM_DIRECTORY:
    case RETRO_ENVIRONMENT_GET_SAVE_DIRECTORY:
        *(const char **)data = system_directory;
        return true;
    case RETRO_ENVIRONMENT_SET_PIXEL_FORMAT:
        pixel_format = *(int *)data;
        return true;
    case RETRO_ENVIRONMENT_GET_LOG_INTERFACE:
        ((struct retro_log_callback *)data)->log = core_log;
        return true;
    case RETRO_ENVIRONMENT_GET_CAN_DUPE:
        *(bool *)data = true;
        return true;
    case RETRO_ENVIRONMENT_GET_VARIABLE: {
        /* core options: only what a test needs, the rest stays at its default */
        struct retro_variable *variable = (struct retro_variable *)data;
        if (strstr(variable->key, "skip_warnings") || strstr(variable->key, "skip_disclaimer")) {
            variable->value = "enabled";
            return true;
        }
        if (strstr(variable->key, "brightness") || strstr(variable->key, "gamma")) {
            variable->value = "1.0";    /* without a value the core's palette loses its shades */
            return true;
        }
        if (strstr(variable->key, "sample_rate")) {
            variable->value = "48000";  /* without a value the core has no sound */
            return true;
        }
        variable->value = NULL;
        return false;
    }
    }
    return false;
}

static void save_screenshot(const void *pixels, unsigned width, unsigned height, size_t pitch)
{
    char path[1024];
    FILE *file;
    unsigned x, y;

    snprintf(path, sizeof path, "%s%06d.ppm", shot_prefix, current_frame);
    file = fopen(path, "wb");
    if (!file) {
        perror(path);
        exit(1);
    }
    fprintf(file, "P6 %u %u 255\n", width, height);
    for (y = 0; y < height; y++) {
        const uint8_t *row = (const uint8_t *)pixels + y * pitch;
        for (x = 0; x < width; x++) {
            uint8_t rgb[3];
            if (pixel_format == RETRO_PIXEL_FORMAT_XRGB8888) {
                uint32_t pixel = ((const uint32_t *)row)[x];
                rgb[0] = pixel >> 16; rgb[1] = pixel >> 8; rgb[2] = pixel;
            } else if (pixel_format == RETRO_PIXEL_FORMAT_RGB565) {
                uint16_t pixel = ((const uint16_t *)row)[x];
                rgb[0] = (pixel >> 11) << 3; rgb[1] = ((pixel >> 5) & 63) << 2; rgb[2] = (pixel & 31) << 3;
            } else {    /* 0RGB1555 */
                uint16_t pixel = ((const uint16_t *)row)[x];
                rgb[0] = ((pixel >> 10) & 31) << 3; rgb[1] = ((pixel >> 5) & 31) << 3; rgb[2] = (pixel & 31) << 3;
            }
            fwrite(rgb, 1, 3, file);
        }
    }
    fclose(file);
}

static void video_refresh(const void *pixels, unsigned width, unsigned height, size_t pitch)
{
    int index;

    if (!pixels)
        return;
    for (index = 0; index < shot_count; index++)
        if (shot_frames[index] == current_frame)
            save_screenshot(pixels, width, height, pitch);
}

static FILE *audio_file;

static void audio_sample(int16_t left, int16_t right)
{
    if (audio_file) {
        fwrite(&left, sizeof left, 1, audio_file);
        fwrite(&right, sizeof right, 1, audio_file);
    }
}

static size_t audio_sample_batch(const int16_t *samples, size_t frames)
{
    if (audio_file)
        fwrite(samples, 2 * sizeof *samples, frames, audio_file);
    return frames;
}
static void input_poll(void) {}

static int16_t input_state(unsigned port, unsigned device, unsigned index, unsigned id)
{
    int item;

    (void)index;
    /* joypad only: the core also asks for keys, and key 9 (Tab, its menu) is not button 9 */
    if (port > 1 || device != RETRO_DEVICE_JOYPAD || id >= JOYPAD_BUTTONS)
        return 0;
    for (item = 0; item < press_count; item++)
        if (presses[item].port == port && presses[item].joypad_id == (int)id && current_frame >= presses[item].frame
            && current_frame < presses[item].frame + PRESS_FRAMES)
            return 1;
    return port == 0 && mashed_buttons[id];
}

/* MASH: every 6 frames, new random directions and attack buttons */
static void mash_buttons(void)
{
    static const int directions[] = { RETRO_DEVICE_ID_JOYPAD_LEFT, RETRO_DEVICE_ID_JOYPAD_RIGHT,
                                      RETRO_DEVICE_ID_JOYPAD_UP, RETRO_DEVICE_ID_JOYPAD_DOWN };
    static const int attacks[] = { RETRO_DEVICE_ID_JOYPAD_Y, RETRO_DEVICE_ID_JOYPAD_X, RETRO_DEVICE_ID_JOYPAD_L,
                                   RETRO_DEVICE_ID_JOYPAD_B, RETRO_DEVICE_ID_JOYPAD_A, RETRO_DEVICE_ID_JOYPAD_R };
    int index;

    if (mash_from_frame < 0 || current_frame < mash_from_frame || current_frame % 6)
        return;
    for (index = 0; index < 4; index++)
        mashed_buttons[directions[index]] = rand() % 100 < 30;
    for (index = 0; index < 6; index++)
        mashed_buttons[attacks[index]] = rand() % 100 < 27;
}

static void parse_press(const char *text)
{
    char buffer[4096], *item;

    strncpy(buffer, text, sizeof buffer - 1);
    buffer[sizeof buffer - 1] = 0;
    for (item = strtok(buffer, ";"); item; item = strtok(NULL, ";")) {
        char text[32];
        const char *name = text;
        unsigned port = 0;
        int frame, index, found = 0;

        if (sscanf(item, "%d:%31s", &frame, text) != 2) {
            fprintf(stderr, "PRESS: cannot read \"%s\"\n", item);
            exit(1);
        }
        if (!strncmp(name, "p2.", 3)) {
            port = 1;
            name += 3;
        }
        for (index = 0; index < BUTTON_NAME_COUNT; index++)
            if (!strcmp(name, button_names[index].name) && press_count < MAXIMUM_ITEMS) {
                presses[press_count].frame = frame;
                presses[press_count].port = port;
                presses[press_count].joypad_id = button_names[index].joypad_id;
                press_count++;
                found = 1;
            }
        if (!found) {
            fprintf(stderr, "PRESS: unknown button \"%s\"\n", name);
            exit(1);
        }
    }
}

static void parse_pokes(const char *text)
{
    char buffer[4096], *item;

    strncpy(buffer, text, sizeof buffer - 1);
    buffer[sizeof buffer - 1] = 0;
    for (item = strtok(buffer, ";"); item; item = strtok(NULL, ";")) {
        struct poke *poke = &pokes[poke_count];

        if (poke_count == MAXIMUM_ITEMS
            || sscanf(item, "%d-%d:%x:%x", &poke->first_frame, &poke->last_frame, &poke->address, &poke->value) != 4) {
            fprintf(stderr, "POKES: cannot read \"%s\"\n", item);
            exit(1);
        }
        poke_count++;
    }
}

/* a list of frame numbers, for SHOTS and DUMPS */
static int parse_frames(const char *text, int *frames)
{
    char buffer[4096], *item;
    int count = 0;

    strncpy(buffer, text, sizeof buffer - 1);
    buffer[sizeof buffer - 1] = 0;
    for (item = strtok(buffer, " ,"); item && count < MAXIMUM_ITEMS; item = strtok(NULL, " ,"))
        frames[count++] = atoi(item);
    return count;
}

/* DUMPS: saves a range of the 68000 memory */
static void dump_memory(unsigned (*read8)(unsigned), unsigned start, unsigned end, const char *name)
{
    char path[1024];
    FILE *file;
    unsigned address;

    snprintf(path, sizeof path, "%s%06d_%s.bin", shot_prefix, current_frame, name);
    file = fopen(path, "wb");
    if (!file) {
        perror(path);
        exit(1);
    }
    for (address = start; address < end; address++)
        fputc(read8(address), file);
    fclose(file);
}

static void write_word(void (*write8)(unsigned, unsigned), unsigned address, unsigned value)
{
    write8(address, value >> 8);
    write8(address + 1, value & 0xff);
}

/* POKES and AUTOWIN for the current frame */
static void write_memory(void (*write8)(unsigned, unsigned))
{
    int index;

    for (index = 0; index < poke_count; index++)
        if (current_frame >= pokes[index].first_frame && current_frame <= pokes[index].last_frame)
            write8(pokes[index].address, pokes[index].value);
    if (autowin_from_frame >= 0 && current_frame >= autowin_from_frame) {
        write_word(write8, PLAYER_1_VITALITY, FULL_VITALITY);
        write_word(write8, PLAYER_1_VITALITY + 2, FULL_VITALITY);
        if (current_frame % 120 == 0) {
            write_word(write8, PLAYER_2_VITALITY, 0);
            write_word(write8, PLAYER_2_VITALITY + 2, 0);
        }
    }
}

static void *core_function(void *core, const char *name)
{
    void *function = dlsym(core, name);

    if (!function) {
        fprintf(stderr, "the core has no %s\n", name);
        exit(1);
    }
    return function;
}

int main(int argc, char **argv)
{
    void *core;
    struct retro_game_info game = { NULL, NULL, 0, NULL };
    void (*write8)(unsigned, unsigned);
    unsigned (*read8)(unsigned);
    void (*run)(void);
    int frame_count;
    /* struct retro_system_av_info: five geometry fields, then fps and sample rate */
    struct { unsigned geometry[4]; float aspect; double fps; double sample_rate; } av_info;

    if (argc != 4) {
        fprintf(stderr, "usage: libretro_run CORE.so GAME.zip FRAMES (see the top of libretro_run.c)\n");
        return 1;
    }
    core = dlopen(argv[1], RTLD_NOW);
    if (!core) {
        fprintf(stderr, "%s\n", dlerror());
        return 1;
    }
    game.path = argv[2];
    frame_count = atoi(argv[3]);

    if (getenv("SYSTEM_DIR")) system_directory = getenv("SYSTEM_DIR");
    if (getenv("OUT")) shot_prefix = getenv("OUT");
    if (getenv("SHOTS")) shot_count = parse_frames(getenv("SHOTS"), shot_frames);
    if (getenv("DUMPS")) dump_count = parse_frames(getenv("DUMPS"), dump_frames);
    if (getenv("PRESS")) parse_press(getenv("PRESS"));
    if (getenv("POKES")) parse_pokes(getenv("POKES"));
    if (getenv("MASH")) mash_from_frame = atoi(getenv("MASH"));
    if (getenv("AUTOWIN")) autowin_from_frame = atoi(getenv("AUTOWIN"));
    srand(getenv("SEED") ? atoi(getenv("SEED")) : 1);

    write8 = (void (*)(unsigned, unsigned))dlsym(core, "retro_dev_write8");
    read8 = (unsigned (*)(unsigned))dlsym(core, "retro_dev_read8");
    if ((!write8 && (poke_count || autowin_from_frame >= 0)) || (!read8 && dump_count)) {
        fprintf(stderr, "POKES, DUMPS and AUTOWIN need a core with mame2003plus-dev-memory.patch\n");
        return 1;
    }

    ((void (*)(bool (*)(unsigned, void *)))core_function(core, "retro_set_environment"))(environment);
    ((void (*)(void *))core_function(core, "retro_set_video_refresh"))(video_refresh);
    ((void (*)(void *))core_function(core, "retro_set_audio_sample"))(audio_sample);
    ((void (*)(void *))core_function(core, "retro_set_audio_sample_batch"))(audio_sample_batch);
    ((void (*)(void *))core_function(core, "retro_set_input_poll"))(input_poll);
    ((void (*)(void *))core_function(core, "retro_set_input_state"))(input_state);
    ((void (*)(void))core_function(core, "retro_init"))();
    if (!((bool (*)(const struct retro_game_info *))core_function(core, "retro_load_game"))(&game)) {
        fprintf(stderr, "the core could not load %s\n", argv[2]);
        return 1;
    }
    ((void (*)(void *))core_function(core, "retro_get_system_av_info"))(&av_info);
    if (getenv("AUDIO")) {
        audio_file = fopen(getenv("AUDIO"), "wb");
        if (!audio_file) {
            perror(getenv("AUDIO"));
            return 1;
        }
    }

    run = (void (*)(void))core_function(core, "retro_run");
    for (current_frame = 0; current_frame < frame_count; current_frame++) {
        mash_buttons();
        int index;

        if (write8)
            write_memory(write8);
        run();
        for (index = 0; index < dump_count; index++)
            if (dump_frames[index] == current_frame) {
                dump_memory(read8, 0x708000, 0x70a000, "sprites");
                dump_memory(read8, 0x90c000, 0x90c400, "palettes");
                dump_memory(read8, 0xff8000, 0xffc000, "ram");
                dump_memory(read8, 0xff0000, 0x1000000, "wram");
            }
    }
    if (audio_file) {
        fclose(audio_file);
        printf("audio: %.0f Hz\n", av_info.sample_rate);
    }
    return 0;
}

# The Windows builder

`vsav2e-builder.exe` is a window that makes `vsav2e.zip` from your own MAME sets. You choose the
folder with `vsav2.zip`, `vsav.zip` and `vhunt2.zip` and the folder for the result, and press
*Build*; it takes about a minute. Nothing is downloaded or sent. The pictures, texts and tools
the build needs (`assets/`, `tools/`, `text/`) are inside the program, so the sets are all it
asks for. When it ends it compares the checksums of the chips with `tools/builder/reference_checksums.txt`
(those of the release it was made from) and says if they match.

## Where it comes from

- `tools/builder/vsav2e_builder.py`: the window (tkinter, the Python standard library) and the
  command-line form (`--cli ROM_FOLDER OUTPUT_FOLDER`); `make_vsav2e.build_set()` is the build.
- `tools/builder/vsav2e_builder.spec`: the PyInstaller recipe (one windowed program with `assets/`
  and the reference checksums as data).
- `.github/workflows/release.yml`: run by hand only (*Actions > Release > Run workflow*, giving the
  version, e.g. `v1.0`; or `gh workflow run release.yml -f version=v1.0`). It builds `vsav2e-builder.exe` on a
  Windows runner and publishes a release with the program, the sources of that commit
  (`vsav2e-source-<version>.zip`) and `SHA256SUMS.txt`.
- `tools/build/paths.py`: where the build finds `assets/`, in a checkout or inside the program.

## When the build changes

Build once from the repository (`python make_vsav2e.py ROMS OUT`) and copy `OUT/vsav2e.checksums.txt`
over `tools/builder/reference_checksums.txt`, then commit, so the program checks against the new
chips.

## Testing

From a checkout or from the frozen program, on any system with a display (or `xvfb-run`):
`VSAV2E_BUILDER_AUTOTEST="ROM_FOLDER|OUTPUT_FOLDER" vsav2e-builder` fills the folders, builds
and closes, printing `AUTOTEST ok` when the chips match. Checked on Linux with PyInstaller; the
Windows program is built by the workflow (not run by me).

## What is inside

The program carries the pictures of the PlayStation and Saturn games that the build uses (see
`assets/`), as the repository does. Keep the repository and its releases private, or leave the
pictures out of the program (the build then falls back to Vampire Savior 2's endings and fails
for the title screen, which needs them).

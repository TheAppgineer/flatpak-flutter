# objectbox_flutter_libs

`objectbox_flutter_libs` downloads the native `objectbox-c` library at build time via
CMake's `FetchContent`, which fails in the Flatpak sandbox (no network access).

The patches replace `FetchContent_Populate` with a check for a pre-downloaded copy at
`${CMAKE_CURRENT_SOURCE_DIR}/../objectbox-c` — the directory where `foreign_deps.json`
extracts the matching `objectbox-c` archive. Flutter includes plugins via a symlink
(`flutter/ephemeral/.plugin_symlinks/<plugin>/linux`); the `../objectbox-c` path
traverses the symlink transparently and resolves correctly to the pub-cache package
directory at the OS level.

## Why `options: ["--binary"]` instead of `use-git: true`

The patch is applied with `patch -p1 --binary` (`"options": ["--binary"]` in the
registry entry) rather than `git apply` (`"use-git": true`).

`git apply` resolves file paths relative to the **git worktree root**, not the `dest`
directory. Because the app build directory is itself a git checkout, `git apply` would
look for `linux/CMakeLists.txt` at the repo root — where it does not exist — and fail
silently, leaving the patch unapplied and causing objectbox to attempt a network
download at CMake time.

`patch -p1 --binary` always applies relative to the current directory (`dest`), which
is the pub-cache package directory that contains `linux/CMakeLists.txt`. The `--binary`
flag is also required to preserve CRLF line endings in the 5.3.2 patch byte-for-byte.

## Why there are two patch files

The `linux/CMakeLists.txt` shipped on pub.dev has LF line endings in version 5.3.1 and
CRLF in 5.3.2. Since `patch --binary` matches context lines byte-for-byte, each patch
must be generated against the file it targets.

The `.gitattributes` file marks `*.patch` as `-text` to prevent Git from normalising
the CRLF context lines in `5.3.2-CMakeLists.txt.patch` on checkout.

## License note (GPL-3.0 apps)

`objectbox-c` is Apache 2.0 with no source code available. **GPL-3.0 apps cannot
use this entry for Flathub submissions.**

The GPL FAQ is explicit: modules that run linked together in a shared address space
"almost surely means combining them into one program", and containers (such as
Flatpak) do not change this analysis. Dynamic linking of `libobjectbox.so` into a
GPL-3.0 app therefore creates a combined work. Since `objectbox-c` provides no
source, the GPL's source-availability requirement for the combined work cannot be
satisfied.

Apps licensed under MIT, Apache 2.0, or other permissive licenses are unaffected.

# Foreign dependencies — maintainer notes

## objectbox_flutter_libs

`objectbox_flutter_libs` downloads the native `objectbox-c` library at build time via
CMake's `FetchContent`, which fails in the Flatpak sandbox (no network access).

The patches replace `FetchContent_Populate` with a check for a pre-downloaded copy at
`${CMAKE_CURRENT_SOURCE_DIR}/../objectbox-c` — the directory where `foreign_deps.json`
extracts the matching `objectbox-c` archive. Flutter includes plugins via a symlink
(`flutter/ephemeral/.plugin_symlinks/<plugin>/linux`); the `../objectbox-c` path
traverses the symlink transparently and resolves correctly to the pub-cache package
directory at the OS level.

## objectbox_sync_flutter_libs

Same as `objectbox_flutter_libs` but for the sync variant: the native archive is
`objectbox-sync-c`, extracted to the same `../objectbox-c` destination (the bundled
library is still named `libobjectbox.so`; the sync build is a superset of the standard
one sharing the same interface).

## Patch application: `options: ["--binary"]` vs `use-git: true`

Both entries use `"options": ["--binary"]` (`patch -p1 --binary`) rather than
`"use-git": true` (`git apply`).

`git apply` resolves file paths relative to the **git worktree root**, not the `dest`
directory. Because the app build directory is itself a git checkout, `git apply` would
look for `linux/CMakeLists.txt` at the repo root — where it does not exist — and fail
silently, leaving `FetchContent` to attempt a network download at CMake time.

`patch -p1 --binary` always applies relative to the current directory (`dest`), which
is the pub-cache package directory that contains `linux/CMakeLists.txt`. The `--binary`
flag is also required to preserve CRLF line endings in the 5.3.2 patch byte-for-byte
(see below).

## Why there are two patch files per package

The `linux/CMakeLists.txt` shipped on pub.dev has LF line endings in version 5.3.1 and
CRLF in 5.3.2 (upstream issue: https://github.com/objectbox/objectbox-dart/issues/811).
Since `patch --binary` matches context lines byte-for-byte, each patch must be generated
against the file it targets. The root `.gitattributes` marks `*.patch` as `-text` to
prevent Git from normalising the CRLF context lines in the 5.3.2 patches on checkout.

## License note (GPL-3.0 apps)

`objectbox-c` and `objectbox-sync-c` are Apache 2.0 with no source code available.
**GPL-3.0 apps cannot use these entries for Flathub submissions.**

The GPL FAQ is explicit: modules that run linked together in a shared address space
"almost surely means combining them into one program", and containers (such as
Flatpak) do not change this analysis. Dynamic linking of `libobjectbox.so` into a
GPL-3.0 app therefore creates a combined work. Since neither library provides source,
the GPL's source-availability requirement for the combined work cannot be satisfied.

Apps licensed under MIT, Apache 2.0, or other permissive licenses are unaffected.

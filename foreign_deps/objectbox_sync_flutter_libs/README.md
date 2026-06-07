# objectbox_sync_flutter_libs

`objectbox_sync_flutter_libs` downloads the native `objectbox-sync-c` library at
build time via CMake's `FetchContent`, which fails in the Flatpak sandbox (no network
access).

The patches replace `FetchContent_Populate` with a check for a pre-downloaded copy at
`${CMAKE_CURRENT_SOURCE_DIR}/../objectbox-c` — the directory where `foreign_deps.json`
extracts the matching `objectbox-sync-c` archive. The bundled library is still named
`libobjectbox.so`; the sync variant is a different build of the same library interface.

## Why there are two patch files

The `linux/CMakeLists.txt` shipped on pub.dev has LF line endings in version 5.3.1 and
CRLF in 5.3.2. Since `patch` matches context lines byte-for-byte, each patch must be
generated against the file it targets.

The `.gitattributes` file marks `*.patch` as `-text` to prevent Git from normalising
the CRLF context lines in `5.3.2-CMakeLists.txt.patch` on checkout.

## License note (GPL-3.0 apps)

`objectbox-sync-c` is licensed under Apache 2.0, which may affect Flathub review if
the main app is GPL-3.0. However, `objectbox_sync_flutter_libs` links to
`libobjectbox.so` dynamically at runtime, keeping the two works legally separate
(GPLv3 §1). Shipping them together inside the isolated Flatpak `/app/lib/` qualifies
as Mere Aggregation (GPLv3 §5), which is explicitly permitted.

Reference: https://www.gnu.org/licenses/gpl-faq.html#MereAggregation

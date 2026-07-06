# Foreign dependencies — maintainer notes

## dart_lmdb2

`dart_lmdb2`'s `LMDBNative._resolveLibraryPath()` (`lib/src/lmdb_native.dart`) locates
`liblmdb.so`/`.dylib`/`.dll` at runtime via `Isolate.resolvePackageUriSync()` on a
`package:dart_lmdb2/...` URI. That API is backed by `.dart_tool/package_config.json` —
a dev-time artifact that only exists next to a JIT run (`dart run`/`flutter run`), not
inside a compiled AOT release build.

**Confirmed empirically, not just reasoned through:** built a scratch Flutter Linux app
depending on `dart_lmdb2`, ran `flutter build linux --release`, copied only
`build/linux/x64/release/bundle/` to an isolated directory (no source project, no
pub-cache — the same shape a Flatpak install has), and ran the binary. It crashed
immediately on the first `LMDB()` construction:

```
Unsupported operation: Isolate.resolvePackageUriSync
#1  LMDBNative._resolveLibraryPath (package:dart_lmdb2/src/lmdb_native.dart:89)
```

This isn't Flatpak-specific — it breaks every compiled Flutter Linux/Windows release
build using `dart_lmdb2`, regardless of how `liblmdb.so` itself was obtained (downloaded
via `fetch_native` or compiled from the vendored `mdb.c`/`midl.c` via `dart run
dart_lmdb2:build`). The patch (`dart_lmdb2/0.9.12-lmdb_native.dart.patch`) tries
`Isolate.resolvePackageUriSync()` first (unchanged dev-time behaviour), then falls back
to a path next to the running executable (`<exe_dir>/lib/<libName>`, matching Flutter's
own native-library bundling convention, confirmed in the same probe:
`build/linux/x64/release/bundle/lib/libapp.so` sits right there) on `UnsupportedError`.

Re-verified after patching, same probe methodology: without `liblmdb.so` present it now
fails with a plain `FileSystemException` instead of crashing; after copying
`liblmdb.so` into `bundle/lib/` (what `flutter_lmdb2`'s Linux support, below, does
automatically), the app opened a real LMDB store successfully.

This is a genuine bug in `dart_lmdb2` itself, worth reporting to
[grammatek/dart_lmdb2](https://github.com/grammatek/dart_lmdb2) — this entry should be
retired once fixed there.

## flutter_lmdb2

`flutter_lmdb2` (the Flutter-plugin wrapper around `dart_lmdb2`, bundling the native
LMDB library into a shipped app) has no Linux (or Windows) support at all as published:
both platforms are commented out in its own `pubspec.yaml`, and there is no `linux/`
directory in the package. Without this, Flutter's plugin-discovery tooling never
touches `dart_lmdb2`'s native library for a Linux build — nothing bundles `liblmdb.so`
into the app at all, regardless of the `dart_lmdb2` fix above.

Two patches, applied together:

- **`flutter_lmdb2/0.9.5-linux-plugin-files.patch`** adds a `linux/` platform directory:
  a minimal no-op GObject plugin (same shape as every other no-op Linux Flutter plugin;
  all real work happens through `dart_lmdb2`'s Dart FFI, not a method channel) and a
  `linux/CMakeLists.txt` that **compiles `liblmdb.so` from source** — `mdb.c`/`midl.c`
  from `LMDB/lmdb.git` at tag `LMDB_0.9.31`, pinned by both tag and commit hash in
  `foreign_deps.json`, fetched via a plain `git` source rather than a prebuilt-binary
  download — and registers the result via the `flutter_lmdb2_bundled_libraries`
  `PARENT_SCOPE` variable, the same convention `objectbox_flutter_libs`'s own
  `linux/CMakeLists.txt` uses to get Flutter's build to copy a library into
  `build/linux/<arch>/release/bundle/lib/`. Also links `Threads::Threads`
  (`find_package(Threads REQUIRED)`) explicitly against the new `lmdb_native` target —
  `mdb.c` uses `pthread_mutex`/pthread-specific data, and while glibc ≥ 2.34 merges
  pthread into `libc.so.6` (making this a no-op on the machine this was developed on,
  confirmed via `ldd -r` showing zero undefined symbols either way), relying on that
  instead of linking explicitly isn't portable to older glibc or non-glibc runtimes.

- **`flutter_lmdb2/0.9.5-pubspec.yaml.patch`** uncomments the `linux:` plugin platform
  block so Flutter's tooling actually picks up the new `linux/` directory.

**Verified empirically, full pipeline:** applied both patches plus the `dart_lmdb2`
patch above, cloned the pinned LMDB tag into `linux/lmdb-src`, built a scratch Flutter
app depending on `flutter_lmdb2`, and ran `flutter build linux --release`:
`build/linux/x64/release/bundle/lib/` contained `liblmdb.so` right next to `libapp.so`,
with zero undefined symbols (`ldd -r`); `.flutter-plugins-dependencies` listed
`flutter_lmdb2` under `"linux"` with `"native_build": true`; copied only `bundle/` to
an isolated directory (no source project, no pub-cache) and ran the binary — `LMDB`
opened successfully. Zero network access, zero prebuilt binaries, at any step.

Unlike `objectbox_flutter_libs`'s own `linux/CMakeLists.txt` (which `FetchContent`s a
prebuilt `objectbox-c` archive), LMDB is compiled from its own real source here —
avoiding a repeat of the licensing complication a prebuilt, no-source binary can create
for GPL-licensed apps.

Like `dart_lmdb2` above, this is a genuine, reportable gap — worth raising with
[grammatek/dart_lmdb2](https://github.com/grammatek/dart_lmdb2) — this entry should be
retired once fixed there.

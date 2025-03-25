# flutter-sdk-generator

Tool to automatically generate `flatpak-builder` manifest json from Flutter SDK.

The module in the generated manifest allows for a Flutter SDK buildup for an offline build.

> Note: Generated manifests are supported by flatpak-builder 1.2.x or newer.

## Downloading Flutter engine and friends

When the `flutter` command is ran for the first time, it normally downloads the Flutter engine first. The generated manifest takes care that these downloads are prefetched and present at build time.

The `tar.gz` files to download are derived from the following `.version` files in de Flutter SDK sources:

* flutter/bin/internal/engine.version
* flutter/bin/internal/gradle_wrapper.version
* flutter/bin/internal/material_fonts.version

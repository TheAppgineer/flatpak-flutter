# offline_manifest_generator

Tool to automatically generate a manifest for offline build from an online counterpart.

The conversion only involves the parts related to the Flutter SDK and the building of the Flutter app.

> Note: Generated manifests are supported by flatpak-builder 1.2.x or newer.

## Conversion steps taken

* The `build-args` for network access are removed
* The `git` entry for flutter is replaced with the matching SDK module, based on the specified tag
* The PATH is adjusted to find the Flutter SDK for the offline build
* The command to activate the SDK (`setup-flutter.sh`) is inserted in the `build-commands`
* The `pubspec-sources.json` manifest is appended to the `sources`

## Manifest preconditions

In order to make the conversion from the online manifest, the following preconditions have to be met:

* The `name` of the module that contains the Flutter app is equal to the last part of the `id` (or `app-id`)
* The `build-system` for the Flutter app module is `simple`

# pubspec-generator

Tool to automatically generate `flatpak-builder` manifest json from a `pubspec.lock`.

The `sources` in the generated manifest allow for a `.pub-cache` buildup for an offline build.

> Note: Generated manifests are supported by flatpak-builder 1.2.x or newer.

## Usage

Convert the locked dependencies by Pub into a format flatpak-builder can understand:

    python3 ./pubspec-generator.py pubspec.lock -o pubspec-sources.json

The output file should be added to the manifest like:

```json
{
    "name": "todo",
    "buildsystem": "simple",
    "build-options": {
      "env": {
        "PUB_CACHE": "/run/build/todo/.pub-cache"
      },
    },
    "build-commands": [
    ],
    "sources": [
        {
            "type": "dir",
            "path": "."
        },
        "pubspec-sources.json"
    ]
}
```

Make sure to override PUB_CACHE env variable to point it to `/run/build/$module-name/.pub-cache` where `$module-name` is the flatpak module name, `todo` in the above example.

For a complete example see the `com.example.todo` Flutter project.

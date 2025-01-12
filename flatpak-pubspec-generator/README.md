# flatpak-pubspec-generator

Tool to automatically generate `flatpak-builder` manifest json from a `pubspec.lock`.

## Requirements

Poetry users can run `poetry install` and skip this.

Otherwise install Python 3.8+ with these modules:
- pyyaml

Generated manifests are supported by flatpak-builder 1.2.x or newer.

## Usage

Poetry users: first activate your virtualenv by running `poetry shell`.

Convert the locked dependencies by Pub into a format flatpak-builder can understand:
```
python3 ./flatpak-pubspec-generator.py pubspec.lock -o pubspec-sources.json
```

The output file should be added to the manifest like:
```json
{
    "name": "quickstart",
    "buildsystem": "simple",
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

Make sure to override PUB_CACHE env variable to point it to `/run/build/$module-name/.pub-cache` where `$module-name` is the flatpak module name, `quickstart` in the above example.

For a complete example see the `com.example.todo` Flutter project.

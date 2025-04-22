# flatpak-flutter
The Flatpak pre-processor for Flutter apps

## Project Goal
The goal of the flatpak-flutter project is to simplify the publishing of Flutter based Linux apps on Flathub.

## The Flathub vs Flutter Status Quo
When a Flutter app is ready for publishing on Flathub then, as part of the PR, the manifest gets build on Flathub infra. At the time the build reaches the first use of the `flutter` tool, it tries to download the Dart SDK and fails in the sandboxed build environment for lack of online access.

For both the Flathub and Flutter project there have been requests to change behavior, but these requests get low priority or are not in line with project policy, keeping the status quo. This limits the options for developers. A Flutter developer who want to publish for Linux is more likely to use Snaps, as that is the supported and documented solution:

https://docs.flutter.dev/deployment/linux

Let's get to a more equal playing field!

> Note: The progress already made is that flatpak-flutter is [referenced](https://docs.flutter.dev/deployment/linux#additional-deployment-resources) on the Flutter documentation site!

### The Common Approach
The approach often taken by Flutter app developers to get their apps published on Flathub, is to create an archive with pre-built binaries and download that within the app manifest. This can lead to the recurring question during the PR review process of "Why not build from source?", but when the reviewer gets aware of the Fluter nature of the app it gets accepted.

### The flatpak-flutter Approach
flatpak-flutter performs a pre-processing run on the app manifest to collect all the required sources for an offline build and stores their origins in the form of flatpak-builder `modules` and `sources`. The output of this pre-processing step is a manifest that can be built in a sandboxed environment, which can be verified locally by running `flatpak-builder` with the `--sandbox` option.

### Why build from source?
With the approach of pre-built binaries it is not certain that the local build used the same library versions as included in the Flatpak Runtime, this can cause compatibility issues.

An added benefit of the source build is that both the x86_64 and aarch64 architecture will be built on the Flathub infra. No longer the need to skip aarch64 support in the `flathub.json` file.

## The flatpak-flutter Workflow
What better way to demonstrate the tool then by building a TODO app :)

<img src="images/flatpak-flutter-todo.png" alt="flatpak-flutter TODO Example" width="600"/>

This workflow chapter uses the `com.example.todo` directory included in the git repository. The `flatpak-flutter.yml` file can be used as an example.

> Note: The TODO app is an unmodified [3th party app](https://github.com/5minslearn/Flutter-Todo-App).

### Create the Manifest
As is the case for every Flatpak, it all starts with the manifest file, but flatpak-flutter eases some criteria to deal with Flutter apps.

> Note: It is recommended to name the manifest `flatpak-flutter.{yml,yaml,json}`, to differentiate it from the generated manifest named after the app-id.

#### Modules
* Name the main module after the app name in the app id
  ```yml
  modules:
    - name: todo
  ```
* Use build system simple
  ```yml
      buildsystem: simple
  ```

#### Build Commands
* Use the Flutter build command, as if it is a local build
  ```yml
      build-commands:
        - flutter build linux --release
  ```
* Add the other commands to install the app and metadata

#### Sources
* Add the git repository of the app
  ```yml
      sources:
        - type: git
          url: https://github.com/5minslearn/Flutter-Todo-App.git
          commit: 2a98e745969dd657efe2eccd964253cd20d13e25
  ```
* Add the git repository of Flutter, use the tag that the app needs
  ```yml
        - type: git
          url: https://github.com/flutter/flutter.git
          tag: 3.29.2
          dest: flutter
  ```
* Add any other dependencies

> Note: The Flutter source entry should have `flutter` as destination directory.

### Pre-process With flatpak-flutter
By passing the manifest to flatpak-flutter it will collect all the dependency sources and generate the manifest for the offline build, to be performed by flatpak-builder. This process pins each dependency to a specific revision, ensuring a reproducible build.

```sh
cd com.example.todo
../flatpak-flutter.py flatpak-flutter.yml
```

> Note: The above generation process only has to be repeated if app dependencies change, or have updates.

#### Conversion steps taken
The conversion steps taken on the manifest to come to the offline manifest are:

* The `git` entry for flutter is replaced with the matching SDK module, based on the specified tag
* The PATH is adjusted to include the Flutter SDK for the offline build
* The command to activate the SDK (`setup-flutter.sh`) is inserted in the `build-commands`
* The `pubspec-sources.json` manifest is appended to the `sources`

#### Command Line Options
```
$ ./flatpak-flutter.py --help
usage: flatpak-flutter.py [-h] [-V] [--app-pubspec PATH]
                          [--extra-pubspecs PATHS] [--from-git URL]
                          [--from-git-branch BRANCH] [--keep-build-dirs]
                          MANIFEST

positional arguments:
  MANIFEST              Path to the manifest

optional arguments:
  -h, --help            show this help message and exit
  -V, --version         show program's version number and exit
  --app-pubspec PATH    Path to the app pubspec
  --extra-pubspecs PATHS
                        Comma separated list of extra pubspec paths
  --from-git URL        Get input files from git repo
  --from-git-branch BRANCH
                        Branch to use in --from-git
  --keep-build-dirs     Don't remove build directories after processing
```

### Build With flatpak-builder
The generated manifest can now to passed to flatpak-builder, to verify correctness.

```sh
flatpak-builder --repo=repo --force-clean --sandbox --user --install --install-deps-from=flathub build com.example.todo.yml
```

> Note: Or use `flatpak run org.flatpak.Builder` instead of `flatpak-builder`.

### Submit to Flathub
With a manifest suitable for a sandboxed build, the [Flathub Submission](https://docs.flathub.org/docs/for-app-authors/submission) can take place.

## The flatpak-flutter Shell Script
The `flatpak-flutter.sh` script, as known from previous releases, is still available as a convenience wrapper around flatpak-flutter and flatpak-builder. Any options given will be passed on to flatpak-flutter.


    ./flatpak-flutter.sh </path/to/app_id> [options]

> Note: The app manifest repo should be named equal to the app ID, as is also required for publishing.

### flatpak.Builder
`flatpak-flutter.sh` uses org.flatpak.Builder, per Flathub's recommendation, install with:

    flatpak install -y flathub org.flatpak.Builder

## Prerequisites
### Python
flatpak-flutter requires Python 3.8 or later and the `pyyaml` package.

Poetry users:
run `poetry install` to setup, activate your virtual env by running `poetry shell`.

Otherwise install Python 3.8+ with the `pyyaml` package:

    pip install pyyaml

## Python module details
The Python modules, taking care of the different processing steps, are further
described in the README file within the module subdirectory:

* [flutter_sdk_generator](flutter_sdk_generator/README.md)
* [pubspec_generator](pubspec_generator/README.md)

> Note: The modules can be executed stand-alone from the command line, use `python3 <module>.py --help` for the specifics.

## Apps Published Using flatpak-flutter

* [CloudOTP](https://flathub.org/apps/com.cloudchewie.cloudotp)
* [Community Remote](https://flathub.org/apps/com.theappgineer.community_remote)
* [Gopeed](https://flathub.org/apps/com.gopeed.Gopeed)
* [Sly](https://flathub.org/apps/page.kramo.Sly)
* Your app here?

> Note: Please get in contact if you know about an app using flatpak-flutter that is not on this list!

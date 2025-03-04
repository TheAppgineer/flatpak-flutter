# flatpak-flutter
Flatpak manifest tooling for the offline build of Flutter apps

## Project Goal
The goal of the flatpak-flutter project is to bridge the gap between the Flatpak and the Flutter project.

The gap being the incompatibility in its connectivity requirements. Flutter requires being online at build time, while Flatpak requires being offline at build time. This incompatibility limits the choice for developers. A Flutter developer who want to publish for Linux is more likely to use Snaps, as that is the supported and documented solution:

https://docs.flutter.dev/deployment/linux

Let's get to a more equal playing field!

## A Three Stage Rocket
These are the three steps that flatpak-flutter takes during the building process:

* Perform a local and online build
* Extract the necessary sources from the online build
* Perform the offline build

Now the reproducible and offline build can be published.
The above process only has to be repeated if app dependencies change or have updates.

## The TODO Example
What better way to demonstrate the tool then by building a TODO app :)

Easily done by executing the flatpak-flutter script:

    ./flatpak-flutter.sh

<img src="images/flatpak-flutter-todo.png" alt="flatpak-flutter TODO Example" width="600"/>

> Note: The TODO app is an unmodified [3th party app](https://github.com/5minslearn/Flutter-Todo-App).

## Flutter App Integration
The basic steps for building any flutter app are:

* Create/adapt the app manifest for online build, name it: `<app_id>/flatpak-flutter.yml`
* Build it!
    ```
    ./flatpak-flutter.sh </path/to/app_id>
    ```

The app manifest repo should be named equal to the app ID, as is also required for publishing.

> Note: For the creation of the online manifest file (`flatpak-flutter.yml`) the included TODO app can be used as an example.

## Selecting the Flutter SDK
It is not necessary to use the latest and greatest Flutter version, just specify the tag of the used SDK version in `flatpak-flutter.yml`.

```
  - type: git
    url: https://github.com/flutter/flutter.git
    tag: 3.29.0
    dest: flutter
```

A subset of SDK versions is included in the form of flatpak-builder modules, if the specified version is not in this subset the matching module will be created during the offline build preparation.

## Apps Published Using flatpak-flutter

* [Community Remote](https://flathub.org/apps/com.theappgineer.community_remote)
* [Gopeed](https://flathub.org/apps/com.gopeed.Gopeed)
* Your app here?

> Note: Please get in contact if you know about an app using flatpak-flutter and not on this list!

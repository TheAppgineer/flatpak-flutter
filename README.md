# flatpak-flutter
Flatpak manifest tooling for the offline build of Flutter apps

## Introduction
flatpak-flutter can help in fulfilling the Flathub publishing requirement to have an offline build, with the additional benifits of building from source.

Being able to build from source makes it easy to also release for the aarch64 architecture (arm64).

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

* Clone the app manifest repo in the root directory of flatpak-flutter
* Create the manifest for online build: `<app_id>/<app_id>-online.yml`
* Create the manifest for offline build: `<app_id>/<app_id>.yml`
* Build it!
    ```
    ./flatpak-flutter.sh <app_id>
    ```

The `app_id` and the app manifest repo should be named equal, as also required for publishing.

> Note: For the creation of the manifest files the included TODO app can be used as an example.

## Apps Published Using flatpak-flutter

* [Community Remote](https://flathub.org/apps/com.theappgineer.community_remote)

> Note: Get in contact if you know about an app using flatpak-flutter and not on this list!

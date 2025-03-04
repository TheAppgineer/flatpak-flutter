#!/bin/bash
VERSION=0.2.0
APP=todo
APP_ID=com.example.$APP
HOME_PATH=$(pwd)

action() {
    echo
    echo -e "\e[32m$1...\e[0m"
}

fail() {
    echo
    echo -e "\e[31mError: $1\e[0m"
}

if [ "$1" != "" ]; then
    MANIFEST_PATH=$1
    APP_ID=$(IFS="/" && read -ra array <<< $MANIFEST_PATH && echo ${array[-1]})
    APP=$(IFS="." && read -ra array <<< $APP_ID && echo ${array[-1]})
else
    MANIFEST_PATH=$APP_ID
fi

if [ ! -d $MANIFEST_PATH ]; then
    action "Checking existence of https://github.com/flathub/$APP_ID.git"
    git -c core.askPass=/bin/true ls-remote -h https://github.com/flathub/$APP_ID.git &> /dev/null

    if [ $? != 0 ]; then
        fail "Neither directory nor remote repository found for $APP_ID"
        exit 1
    fi

    action "Cloning https://github.com/flathub/$APP_ID.git"
    git clone --recursive https://github.com/flathub/$APP_ID.git $MANIFEST_PATH
fi

cd $MANIFEST_PATH

FLUTTER_VERSION=$(python3 $HOME_PATH/offline-manifest-generator/offline-manifest-generator.py flatpak-flutter.yml)

if [ $? != 0 ]; then
    fail "Failed to convert to offline mode"
fi

echo -e "flatpak-flutter version:\t$VERSION"
echo -e "Building App ID:\t\t$APP_ID"
echo -e "Targeting Flutter SDK version:\t$FLUTTER_VERSION"
echo
echo "To change build target: ./flatpak-flutter.sh </path/to/app_id>"

BUILD_PATH=.flatpak-builder/build/$APP
FLUTTER_PATH=$BUILD_PATH/flutter

if [ -f $HOME_PATH/releases/$FLUTTER_VERSION/*.flutter.patch ]; then
    action "Getting patches for Flutter $FLUTTER_VERSION"
    cp $HOME_PATH/releases/$FLUTTER_VERSION/*.flutter.patch .
fi

if [ ! -f flatpak-flutter.yml ]; then
    fail "Expected to find online manifest: flatpak-flutter.yml"
fi

action "Starting online build"
flatpak run org.flatpak.Builder --repo=repo --force-clean --user --install-deps-from=flathub --build-only --keep-build-dirs build flatpak-flutter.yml

if [ $? != 0 ]; then
    fail "Online build failed, please verify output for details"
    exit 1
fi

if [ -d $FLUTTER_PATH ]; then
    action "Collecting sources for offline build"
    set -e
    python3 $HOME_PATH/flatpak-pubspec-generator/flatpak-pubspec-generator.py $BUILD_PATH/pubspec.lock -o pubspec-sources-$APP.json
    python3 $HOME_PATH/flatpak-pubspec-generator/flatpak-pubspec-generator.py $FLUTTER_PATH/packages/flutter_tools/pubspec.lock -o pubspec-sources-flutter.json
    cp $FLUTTER_PATH/packages/flutter_tools/.dart_tool/package_config.json .
    set +e

    if [ -x flatpak-flutter/custom-sources.sh ]; then
        action "Collecting custom sources for offline build"
        ./flatpak-flutter/custom-sources.sh $BUILD_PATH
    fi
fi

if [ ! -f pubspec-sources-$APP.json ]; then
    fail "No sources found for offline build!"
    exit 1
fi

if [ -f $HOME_PATH/releases/$FLUTTER_VERSION/flutter-sdk.json ]; then
    cp -r $HOME_PATH/releases/$FLUTTER_VERSION/flutter-sdk.json flutter-sdk-$FLUTTER_VERSION.json
else
    action "Generating Flutter SDK for version $FLUTTER_VERSION"
    python3 $HOME_PATH/flutter-sdk-generator/flutter-sdk-generator.py $FLUTTER_PATH -o flutter-sdk-$FLUTTER_VERSION.json
fi

cp -r $HOME_PATH/releases/flutter-shared.sh.patch .

action "Starting offline build"
flatpak run org.flatpak.Builder --repo=repo --force-clean --user --install --install-deps-from=flathub build $APP_ID.yml

if [ $? != 0 ]; then
    fail "Offline build failed, please verify output for details"
    exit 1
fi

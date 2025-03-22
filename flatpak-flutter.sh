#!/bin/bash
VERSION=0.3.3
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
    exit 1
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
    fi

    action "Cloning https://github.com/flathub/$APP_ID.git"
    git clone --recursive https://github.com/flathub/$APP_ID.git $MANIFEST_PATH
fi

cd $MANIFEST_PATH

if [ -f flatpak-flutter.yml ]; then
    MANIFEST_TYPE=yml
elif [ -f flatpak-flutter.json ]; then
    MANIFEST_TYPE=json
else
    fail "No flatpak-flutter.{yml,json} found"
fi

FLUTTER_VERSION=$(python3 $HOME_PATH/offline-manifest-generator/offline-manifest-generator.py flatpak-flutter.$MANIFEST_TYPE)

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

action "Starting online build"
flatpak run org.flatpak.Builder --force-clean --user --install-deps-from=flathub --build-only --keep-build-dirs build flatpak-flutter.$MANIFEST_TYPE

if [ $? != 0 ]; then
    fail "Online build failed, please verify output for details"
fi

if [ -d $FLUTTER_PATH ]; then
    action "Collecting sources for offline build"
    set -e
    python3 $HOME_PATH/pubspec-generator/pubspec-generator.py $BUILD_PATH/pubspec.lock
    python3 $HOME_PATH/pubspec-generator/pubspec-generator.py $FLUTTER_PATH/packages/flutter_tools/pubspec.lock -a
    cp $FLUTTER_PATH/packages/flutter_tools/.dart_tool/package_config.json .
    set +e

    if [ -x flatpak-flutter/custom-sources.sh ]; then
        action "Collecting custom sources for offline build"
        ./flatpak-flutter/custom-sources.sh $BUILD_PATH $HOME_PATH
    fi

    rm -rf $BUILD_PATH-*
fi

if [ ! -f pubspec-sources*.json ]; then
    fail "No sources found for offline build!"
fi

if [ -f $HOME_PATH/releases/$FLUTTER_VERSION/flutter-sdk.json ]; then
    cp -r $HOME_PATH/releases/$FLUTTER_VERSION/flutter-sdk.json flutter-sdk-$FLUTTER_VERSION.json
else
    action "Generating Flutter SDK for version $FLUTTER_VERSION"
    python3 $HOME_PATH/flutter-sdk-generator/flutter-sdk-generator.py $FLUTTER_PATH -o flutter-sdk-$FLUTTER_VERSION.json
fi

cp -r $HOME_PATH/releases/flutter-shared.sh.patch .

action "Starting offline build"
flatpak run org.flatpak.Builder --repo=repo --force-clean --sandbox --user --install --install-deps-from=flathub build $APP_ID.$MANIFEST_TYPE

if [ $? != 0 ]; then
    fail "Offline build failed, please verify output for details"
fi

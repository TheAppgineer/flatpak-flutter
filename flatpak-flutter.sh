#!/bin/bash
VERSION=0.1.0
APP=todo
APP_ID=com.example.$APP
FLUTTER_VERSION=3.29.0

action() {
    echo
    echo -e "\e[32m$1...\e[0m"
}

fail() {
    echo
    echo -e "\e[31mError: $1\e[0m"
}

if [ "$1" != "" ]; then
    APP_ID=$1
    APP=$(IFS="." && read -ra array <<< $APP_ID && echo ${array[-1]})
fi

if [ "$2" != "" ]; then
    FLUTTER_VERSION=$2
fi

echo -e "flatpak-flutter version:\t$VERSION"
echo -e "Building App ID:\t\t$APP_ID"
echo -e "Targeting Flutter SDK version:\t$FLUTTER_VERSION"
echo
echo "To change build target: ./flatpak-flutter.sh <app_id> <sdk_version>"

BUILD_PATH=.flatpak-builder/build/$APP
FLUTTER_PATH=$BUILD_PATH/flutter

if [ ! -d $APP_ID ]; then
    action "Checking existence of https://github.com/flathub/$APP_ID.git"
    git -c core.askPass=/bin/true ls-remote -h https://github.com/flathub/$APP_ID.git &> /dev/null

    if [ $? != 0 ]; then
        fail "Neither directory nor remote repository found for $APP_ID"
        exit 1
    fi

    action "Cloning https://github.com/flathub/$APP_ID.git"
    git clone --recursive https://github.com/flathub/$APP_ID.git
fi

cd $APP_ID

if [ -f ../releases/$FLUTTER_VERSION/*.patch ]; then
    action "Getting patches for Flutter $FLUTTER_VERSION"
    cp ../releases/$FLUTTER_VERSION/*.patch .
fi

if [ ! -f $APP_ID-online.yml ]; then
    fail "Expected to find online manifest: $APP_ID-online.yml"
fi

action "Starting online build"
flatpak run org.flatpak.Builder --repo=repo --force-clean --user --install-deps-from=flathub --build-only --keep-build-dirs build $APP_ID-online.yml

if [ $? != 0 ]; then
    fail "Online build failed, please verify output for details"
    exit 1
fi

if [ -d $FLUTTER_PATH ]; then
    action "Collecting sources for offline build"
    python3 ../flatpak-pubspec-generator/flatpak-pubspec-generator.py $BUILD_PATH/pubspec.lock -o pubspec-sources-$APP.json
    python3 ../flatpak-pubspec-generator/flatpak-pubspec-generator.py $FLUTTER_PATH/packages/flutter_tools/pubspec.lock -o pubspec-sources-flutter.json
    cp $FLUTTER_PATH/packages/flutter_tools/.dart_tool/package_config.json .

    if [ -x custom-sources.sh ]; then
        action "Collecting custom sources for offline build"
        ./custom-sources.sh $BUILD_PATH
    fi
fi

if [ ! -f pubspec-sources-$APP.json ]; then
    fail "No sources found for offline build!"
    exit 1
fi

if [ -f ../releases/$FLUTTER_VERSION/flutter-sdk.json ]; then
    cp -r ../releases/$FLUTTER_VERSION/flutter-sdk.json flutter-sdk-$FLUTTER_VERSION.json
else
    action "Generating Flutter SDK for version $FLUTTER_VERSION"
    python3 ../flutter-sdk-generator/flutter-sdk-generator.py $FLUTTER_PATH -o flutter-sdk-$FLUTTER_VERSION.json
fi

cp -r ../releases/flutter-shared.sh.patch .

action "Starting offline build"
flatpak run org.flatpak.Builder --repo=repo --force-clean --user --install --install-deps-from=flathub build $APP_ID.yml

if [ $? != 0 ]; then
    fail "Offline build failed, please verify output for details"
    exit 1
fi

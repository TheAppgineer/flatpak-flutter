#!/bin/bash
APP=todo
APP_ID=com.example.$APP
FLUTTER_VERSION=3.27.2

if [ "$1" != "" ]; then
    APP_ID=$1
    APP=$(IFS="." && read -ra array <<< $APP_ID && echo ${array[-1]})
fi

if [ "$2" != "" ]; then
    FLUTTER_VERSION=$2
fi

BUILD_PATH=.flatpak-builder/build/$APP
FLUTTER_PATH=$BUILD_PATH/flutter

cd $APP_ID

echo "Starting online build..."
echo
flatpak run org.flatpak.Builder --repo=repo --force-clean --user --install-deps-from=flathub --build-only --keep-build-dirs build $APP_ID-online.yml

if [ $? != 0 ]; then
    echo
    echo "Online build failed, please verify output for details"
    exit 1
fi

if [ -d $FLUTTER_PATH ]; then
    echo
    echo "Collecting sources for offline build..."
    python3 ../flatpak-pubspec-generator/flatpak-pubspec-generator.py $BUILD_PATH/pubspec.lock -o pubspec-sources-$APP.json
    python3 ../flatpak-pubspec-generator/flatpak-pubspec-generator.py $FLUTTER_PATH/packages/flutter_tools/pubspec.lock -o pubspec-sources-flutter.json
    cp $FLUTTER_PATH/packages/flutter_tools/.dart_tool/package_config.json .

    if [ -x custom-sources.sh ]; then
        echo
        echo "Collecting custom sources for offline build..."
        ./custom-sources.sh $BUILD_PATH
    fi
fi

if [ ! -f pubspec-sources-$APP.json ]; then
    echo
    echo "No sources found for offline build!"
    exit 1
fi

if [ -f ../releases/$FLUTTER_VERSION/flutter-sdk.json ]; then
    cp -r ../releases/$FLUTTER_VERSION/flutter-sdk.json flutter-sdk-$FLUTTER_VERSION.json
else
    echo
    echo "Generating Flutter SDK for version $FLUTTER_VERSION..."
    python3 ../flutter-sdk-generator/flutter-sdk-generator.py $FLUTTER_PATH -o flutter-sdk-$FLUTTER_VERSION.json
fi

cp -r ../releases/flutter-shared.sh.patch .

echo
echo "Starting offline build..."
echo
flatpak run org.flatpak.Builder --repo=repo --force-clean --user --install --install-deps-from=flathub build $APP_ID.yml

if [ $? != 0 ]; then
    echo
    echo "Offline build failed, please verify output for details"
    exit 1
fi

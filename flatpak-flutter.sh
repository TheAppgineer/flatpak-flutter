#!/bin/bash
VERSION=0.4.0
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

if [ $# != 0 ]; then
    MANIFEST_PATH=$1
    APP_ID=$(IFS="/" && read -ra array <<< $MANIFEST_PATH && echo ${array[-1]})
    APP=$(IFS="." && read -ra array <<< $APP_ID && echo ${array[-1]})
    shift
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
elif [ -f flatpak-flutter.yaml ]; then
    MANIFEST_TYPE=yaml
elif [ -f flatpak-flutter.json ]; then
    MANIFEST_TYPE=json
else
    fail "No flatpak-flutter.{yml,yaml,json} found"
fi

echo -e "flatpak-flutter version:\t$VERSION"
echo -e "Building App ID:\t\t$APP_ID"
echo
echo "To change build target: ./flatpak-flutter.sh </path/to/app_id> [options]"

action "Starting online build"
$HOME_PATH/flatpak-flutter.py $@ flatpak-flutter.$MANIFEST_TYPE

if [ $? != 0 ]; then
    fail "Online build failed, please verify output for details"
fi

if [ ! -f pubspec-sources*.json ]; then
    fail "No sources found for offline build!"
fi

action "Starting offline build"
flatpak run org.flatpak.Builder --repo=repo --force-clean --sandbox --user --install --install-deps-from=flathub build $APP_ID.$MANIFEST_TYPE

if [ $? != 0 ]; then
    fail "Offline build failed, please verify output for details"
fi

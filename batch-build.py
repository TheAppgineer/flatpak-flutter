#!/usr/bin/env python3

__license__ = 'MIT'
import argparse
import json
import os
import shutil
import subprocess
import sys

from pathlib import Path

version = __import__("flatpak-flutter").__version__


def run(script: bool, command: list[str]) -> int:
    if script:
        print(' '.join(command))
        return 0
    else:
        return subprocess.run(command).returncode


def chdir(script: bool, path: str):
    if script:
        print(f'cd {path}')
    else:
        os.chdir(path)


def rmtree(script: bool, path: str):
    if script:
        print(f'rm -rf {path}')
    else:
        shutil.rmtree(path)


def makedirs(script: bool, path: str):
    if script:
        print(f'mkdir -p {path}')
    else:
        os.makedirs(path, exist_ok=True)


def prepare(root: str, name: str, clean: bool, script: bool):
    path = f'{root}/{name}'

    if script:
        print(f'\n\n# === Preparing: {name} ===\n')

    if os.path.isdir(path):
        remote = False

        if clean and os.path.isdir(f'{path}/.flatpak-builder'):
            rmtree(script, f'{path}/.flatpak-builder')
    else:
        remote = True
        makedirs(script, path)

    chdir(script, path)

    return remote


def preprocess(flatpak_flutter_root: str, app, remote: bool, script: bool):
        print(f'\n\n# === Preprocessing: {app["name"]} ===\n')

        prepro = [
            f'{flatpak_flutter_root}/flatpak-flutter.py',
            f'flatpak-flutter{app["suffix"]}',
        ]

        if remote or 'url' in app:
            url = app['url'] if 'url' in app else f'https://github.com/flathub/{app["name"]}.git'
            prepro += [
                '--from-git',
                url,
            ]

        if 'options' in app:
            prepro += app['options']

        return run(script, prepro)


def build(name: str, suffix: str, script: bool, install: bool):
    print(f'\n\n# === Building: {name} ===\n')

    build = [
        'flatpak-builder',
        '--repo',
        '../repo',
        '--force-clean',
        '--sandbox',
        '--install-deps-from',
        'flathub',
        'build',
        f'{name}{suffix}',
    ]

    if install:
        index = build.index('build')
        build.insert(index, '--user')
        build.insert(index, '--install')

    return run(script, build)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('APPS_JSON', help='Path to the apps.json file')
    parser.add_argument('-V', '--version', action='version', version=f'%(prog)s-{version}')
    parser.add_argument('-y', '--yes', action='store_true', help="Answer all questions with yes")
    parser.add_argument('-c', '--clean', action='store_true', help="Perform clean flatpak-builder builds")
    parser.add_argument('-i', '--install', action='store_true', help="Perform (user) install after build")
    parser.add_argument('-s', '--script', action='store_true', help="Script the commands instead of executing")

    args = parser.parse_args()
    apps_json = args.APPS_JSON

    if Path(apps_json).suffix != '.json':
        if os.path.isfile(f'{apps_json}/apps.json'):
            apps_json = f'{apps_json}/apps.json'
        else:
            print('Error: no json file specified')
            exit(1)

    flatpak_flutter_root = Path(sys.argv[0]).resolve().parent
    json_path = Path(apps_json).resolve()
    root = json_path.parent

    with open(json_path, 'r') as content:
        apps = json.load(content)

    if args.script:
        print('#!/bin/bash')
    elif not args.yes and input('Continue (y/N)? ') != 'y':
        exit(1)

    count = len(apps)

    if count > 1:
        print(f'\n# === A total of {count} applications will be built, this will take time and disk space!! ===')

    for app in apps:
        remote = prepare(root, app['name'], args.clean, args.script)
        return_code = preprocess(flatpak_flutter_root, app, remote, args.script)

        if return_code:
            print(f'Error: flatpak-flutter failed with return code {return_code}')
            exit(1)

        return_code = build(app['name'], app['suffix'], args.script, args.install)

        if return_code:
            print(f'Error: flatpak-builder failed with return code {return_code}')
            exit(1)

        chdir(args.script, '..')


if __name__ == '__main__':
    main()

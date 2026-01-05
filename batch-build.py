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

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('APPS_JSON', help='Path to the apps.json file')
    parser.add_argument('-V', '--version', action='version', version=f'%(prog)s-{version}')
    parser.add_argument('-y', '--yes', action='store_true', help="Answer all questions with yes")
    parser.add_argument('-c', '--clean', action='store_true', help="Perform clean flatpak-builder builds")

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

    print(f'\n=== A total of {len(apps)} apps will be built, this will take time and disk space!! ===\n')
    print(f'Root directory: {root}\n')

    if not args.yes and input('Continue (y/N)? ') != 'y':
        exit(1)

    for app in apps:
        path = f'{root}/{app["name"]}'

        if os.path.isdir(path):
            remote = False

            if args.clean and os.path.isdir(f'{path}/.flatpak-builder'):
                shutil.rmtree(f'{path}/.flatpak-builder')
        else:
            remote = True
            os.makedirs(path, exist_ok=True)

        os.chdir(path)

        print(f'\n\n=== Preprocessing: {app["name"]} ===\n')

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

        return_code = subprocess.run(prepro).returncode

        if return_code:
            print(f'Error: flatpak-flutter failed with return code {return_code}')
            exit(1)

        print(f'\n\n=== Building: {app["name"]} ===\n')

        build = [
            'flatpak-builder',
            '--repo',
            '../repo',
            '--force-clean',
            '--sandbox',
            '--install-deps-from',
            'flathub',
            'build',
            f'{app["name"]}{app["suffix"]}',
        ]

        return_code = subprocess.run(build).returncode

        if return_code:
            print(f'Error: flatpak-builder failed with return code {return_code}')
            exit(1)

        os.chdir('..')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3

__license__ = 'MIT'
import subprocess
import os
import yaml
import glob

from typing import Tuple
from pubspec_generator.pubspec_generator import PUB_CACHE


FLUTTER_URL = 'https://github.com/flutter/flutter.git'


class Dumper(yaml.Dumper):
    def increase_indent(self, flow=False, *args, **kwargs):
        return super().increase_indent(flow=flow, indentless=False)


def _fetch_with_git(url: str, ref: str, fetch_path: str):
    options = [
        'git',
        'clone',
        '--branch',
        ref,
        '--depth',
        '1',
        url,
        fetch_path,
    ]

    try:
        subprocess.run(options, stdout=subprocess.PIPE, check=True)
    except subprocess.CalledProcessError:
        command = [f'git clone {url} {fetch_path} && cd {fetch_path} && git reset --hard {ref}']
        subprocess.run(command, stdout=subprocess.PIPE, shell=True, check=True)


def _process_build_options(module):
    if 'build-options' in module:
        build_options = module['build-options']

        if 'build-args' in build_options:
            build_args = build_options['build-args']

            for (idx, build_arg) in enumerate(build_args):
                if build_arg == '--share=network':
                    del build_args[idx]

                    if len(build_args) == 0:
                        del build_options['build-args']

        if 'append-path' in build_options:
            paths = str(build_options['append-path']).split(':')
            for (idx, path) in enumerate(paths):
                if path.endswith('flutter/bin'):
                    del paths[idx]
                    paths.insert(idx, '/var/lib/flutter/bin')
                    build_options['append-path'] = ':'.join(paths)
                    break


def _process_build_commands(module):
    if 'build-commands' in module:
        insert_commands = ['mkdir -p build/native_assets/linux', 'setup-flutter.sh']
        build_commands = list(module['build-commands'])

        for idx, command in enumerate(build_commands):
            if str(command).startswith('flutter pub get'):
                del build_commands[idx]
                for command in reversed(insert_commands):
                    build_commands.insert(idx, command)
                break

            if str(command).startswith('flutter '):
                for command in reversed(insert_commands):
                    build_commands.insert(idx, command)
                break

        module['build-commands'] = build_commands


def _process_sources(module, fetch_path: str):
    if not 'sources' in module:
        return

    sources = module['sources']

    idxs = []
    for (idx, source) in enumerate(sources):
        if 'type' in source:
            if source['type'] == 'git':
                if not 'url' in source:
                    continue

                if 'tag' in source:
                    ref = source['tag']
                elif 'commit' in source:
                    ref = source['commit']
                else:
                    continue

                if source['url'] == FLUTTER_URL and 'tag' in source:
                    _fetch_with_git(source['url'], ref, f'{fetch_path}/flutter')
                    idxs.append(idx)

                    if 'modules' in module:
                        module['modules'] += [f"flutter-sdk-{source['tag']}.json"]
                    else:
                        module['modules'] = [f"flutter-sdk-{source['tag']}.json"]

                    tag = source['tag']
                else:
                    _fetch_with_git(source['url'], ref, fetch_path)

            if source['type'] == 'patch' and '.flutter.patch' in str(source['path']):
                idxs.append(idx)

    for idx in reversed(idxs):
        del sources[idx]

    for patch in glob.glob('*.offline.patch'):
        sources += [
            {
                'type': 'patch',
                'path': patch
            }
        ]

    sources += ["pubspec-sources.json"]
    return tag


def _get_flutter_pub(build_path_app: str, pubspec_path = None):
    full_pubspec_path = build_path_app if pubspec_path is None else f'{build_path_app}/{pubspec_path}'
    pub_cache = f'{os.getcwd()}/{build_path_app}/.{PUB_CACHE}'
    flutter = 'flutter/bin/flutter'
    options = f'PUB_CACHE={pub_cache} {build_path_app}/{flutter} pub get -C {full_pubspec_path}'

    subprocess.run([options], stdout=subprocess.PIPE, shell=True, check=True)


def fetch_flutter_app(manifest, build_path: str) -> Tuple[str, str, int]:
    if 'app-id' in manifest:
        app_id = 'app-id'
    elif 'id' in manifest:
        app_id = 'id'
    else:
        exit(1)

    app_id_parts = str(manifest[app_id]).split('.')
    app = app_id_parts[len(app_id_parts) - 1]

    if not 'modules' in manifest:
        exit(1)

    for module in manifest['modules']:
        if not 'name' in module or module['name'] != app:
            continue

        if not 'buildsystem' in module or module['buildsystem'] != 'simple':
            print('Currently only the simple build system is supported')
            exit(1)

        break

    _process_build_options(module)
    _process_build_commands(module)

    build_path_app = f'{build_path}/{app}'
    build_id = len(glob.glob(f'{build_path_app}-*')) + 1
    tag = _process_sources(module, f'{build_path_app}-{build_id}')

    options = [f'cd {build_path} && ln -snf {app}-{build_id} {app}']
    subprocess.run(options, stdout=subprocess.PIPE, shell=True, check=True)

    _get_flutter_pub(build_path_app)

    return manifest[app_id], tag, build_id

__license__ = 'MIT'
import subprocess
import yaml
import glob
import shutil

from pathlib import Path
from typing import Tuple
from pubspec_generator.pubspec_generator import PUB_CACHE


FLUTTER_URL = 'https://github.com/flutter/flutter.git'


class Dumper(yaml.Dumper):
    def increase_indent(self, flow=False, *args, **kwargs):
        return super().increase_indent(flow=flow, indentless=False)


def _fetch_repos(repos: list):
    def by_path_depth(fetch_repo):
        return len(str(fetch_repo[2]).split('/'))

    repos.sort(key=by_path_depth)

    for url, ref, path in repos:
        options = [
            'git',
            'clone',
            '--branch',
            ref,
            '--depth',
            '1',
            url,
            path,
        ]

        try:
            subprocess.run(options, stdout=subprocess.PIPE, check=True)
        except subprocess.CalledProcessError:
            command = [f'git clone {url} {path} && cd {path} && git reset --hard {ref}']
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


def _process_sources(module, fetch_path: str, releases_path: str):
    if not 'sources' in module:
        return

    sources = module['sources']
    idxs = []
    repos = []

    for idx, source in enumerate(sources):
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

                if 'dest' in source:
                    dest = str(source['dest'])
                    repos.append((source['url'], ref, f'{fetch_path}/{dest}'))
                else:
                    repos.append((source['url'], ref, fetch_path))

                if source['url'] == FLUTTER_URL and 'tag' in source:
                    idxs.append(idx)

                    if 'modules' in module:
                        module['modules'] += [f"flutter-sdk-{source['tag']}.json"]
                    else:
                        module['modules'] = [f"flutter-sdk-{source['tag']}.json"]

                    tag = source['tag']

            if source['type'] == 'patch' and '.flutter.patch' in str(source['path']):
                idxs.append(idx)

    _fetch_repos(repos)

    for patch in glob.glob(f'{releases_path}/{tag}/*.flutter.patch'):
        shutil.copyfile(patch, Path(patch).name)

    for source in sources:
        if 'type' in source:
            if source['type'] == 'patch':
                if not 'path' in source:
                    continue

                path = str(source['path'])
                print(f'Apply patch: {path}')
                command = f'(cd {fetch_path} && patch -p1) < {path}'
                subprocess.run([command], stdout=subprocess.PIPE, shell=True, check=True)

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


def fetch_flutter_app(manifest, build_path: str, releases_path: str) -> Tuple[str, str, int]:
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
            print('Error: Only the simple build system is supported')
            exit(1)

        _process_build_options(module)
        _process_build_commands(module)

        build_path_app = f'{build_path}/{app}'
        build_id = len(glob.glob(f'{build_path_app}-*')) + 1
        tag = _process_sources(module, f'{build_path_app}-{build_id}', releases_path)

        options = [f'cd {build_path} && ln -snf {app}-{build_id} {app}']
        subprocess.run(options, stdout=subprocess.PIPE, shell=True, check=True)

        return manifest[app_id], tag, build_id
    else:
        print(f'Error: No module named {app} found!')
        exit(1)

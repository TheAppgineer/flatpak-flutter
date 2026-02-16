__license__ = 'MIT'
import subprocess
import yaml
import glob
import os
import shutil
import sys

from git_actions.git_actions import fetch_repos, get_commit, get_tag
from pathlib import Path


FLUTTER_URL = 'https://github.com/flutter/flutter'


class Dumper(yaml.Dumper):
    def increase_indent(self, flow=False, *args, **kwargs):
        return super().increase_indent(flow=flow, indentless=False)


def _search_submodules(gitmodules) -> str | None:
    def get_flutter_path() -> str | None:
        if ('url' in submodule and 'path' in submodule and
                (submodule['url'] == FLUTTER_URL or submodule['url'] == f'{FLUTTER_URL}.git')):
            return str(submodule['path'])

    with open(gitmodules, 'r') as input:
        lines = input.readlines()
        submodule = {}

        for line in lines:
            line = line.strip()
            key_value = line.split(' = ')

            if line.startswith('[') and line.endswith(']'):
                path = get_flutter_path()
                submodule.clear()

            if path is not None:
                return path

            if len(key_value) == 2:
                submodule[key_value[0]] = key_value[1]

    return get_flutter_path()


def _process_build_options(module, sdk_path: str):
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
                if path.endswith(f'{sdk_path}/bin'):
                    del paths[idx]
                    paths.insert(idx, '/var/lib/flutter/bin')
                    build_options['append-path'] = ':'.join(paths)
                    break


def _process_build_commands(module, app_pubspec: str) -> str:
    if not app_pubspec:
        insert_command = 'setup-flutter.sh'

        if 'subdir' in module:
            app_pubspec = str(module['subdir'])
        else:
            app_pubspec = '.'
    else:
        insert_command = f'setup-flutter.sh -C {app_pubspec}'

    if 'build-commands' in module:
        build_commands = list(module['build-commands'])

        for idx, command in enumerate(build_commands):
            if str(command).startswith('flutter pub get'):
                del build_commands[idx]
                build_commands.insert(idx, insert_command)
                break

            if 'flutter ' in str(command) or 'dart ' in str(command):
                build_commands.insert(idx, insert_command)
                break

        module['build-commands'] = build_commands

    return app_pubspec


def _process_sources(module, fetch_path: str, releases_path: str, no_shallow: bool):
    idxs = []
    repos = []
    tag = None
    sdk_path = None
    sources = module['sources'] if 'sources' in module else []

    for idx, source in enumerate(sources):
        if 'type' in source:
            if source['type'] == 'git':
                if not 'url' in source:
                    continue

                if 'tag' in source:
                    ref = str(source['tag'])
                elif 'commit' in source:
                    ref = str(source['commit'])
                else:
                    ref = None

                shallow = False if no_shallow or 'disable-shallow-clone' in source else True
                recursive = False if 'disable-submodules' in source else True

                if 'dest' in source:
                    dest = str(source['dest'])
                    repos.append((source['url'], ref, f'{fetch_path}/{dest}', shallow, recursive))
                else:
                    repos.append((source['url'], ref, fetch_path, shallow, recursive))

                if str(source['url']).startswith(FLUTTER_URL) and 'tag' in source:
                    idxs.append(idx)
                    tag = ref
                    sdk_path = dest

            if source['type'] == 'patch' and '.flutter.patch' in str(source['path']):
                idxs.append(idx)

            if source['type'] == 'dir' and 'path' in source:
                print(f'Warning: Skipping dir: {source['path']}', file=sys.stderr)

    fetch_repos(repos)

    gitmodules = f'{fetch_path}/.gitmodules'

    if tag is None and os.path.isfile(gitmodules):
        sdk_path = _search_submodules(gitmodules)

        if sdk_path:
            tag = get_tag(f'{fetch_path}/{sdk_path}')

    for patch in glob.glob(f'{releases_path}/{tag}/*.flutter.patch'):
        shutil.copyfile(patch, Path(patch).name)

    # With the repos fetched, any file access can be performed
    for source in sources:
        if 'type' in source:
            dest = f'{fetch_path}/{source["dest"]}' if 'dest' in source else fetch_path

            if source['type'] == 'patch':
                if not 'path' in source:
                    continue

                path = str(source['path'])

                if os.path.isdir(dest):
                    print(f'Apply patch: {path}')
                    command = f'(cd {dest} && patch -p1) < {path}'
                    subprocess.run([command], stdout=subprocess.PIPE, shell=True, check=True)
                else:
                    print(f'Warning: Skipping patch {path}, directory {dest} does not exist', file=sys.stderr)
            elif source['type'] == 'git' and 'commit' not in source:
                source['commit'] = get_commit(dest)

    for idx in reversed(idxs):
        del sources[idx]

    for patch in glob.glob('*.offline.patch'):
        sources += [
            {
                'type': 'patch',
                'path': patch
            }
        ]

    return tag, sdk_path


def fetch_flutter_app(
    manifest,
    app_module: str,
    build_path: str,
    releases_path: str,
    app_pubspec: str,
    no_shallow: bool,
):
    if 'app-id' in manifest:
        app_id = 'app-id'
    elif 'id' in manifest:
        app_id = 'id'
    else:
        exit(1)

    app = app_module if app_module is not None else str(manifest[app_id]).split('.')[-1]

    if not 'modules' in manifest:
        exit(1)

    for module in manifest['modules']:
        if not 'name' in module or str(module['name']).lower() != app.lower():
            continue

        if not 'buildsystem' in module or module['buildsystem'] != 'simple':
            print('Error: Only the simple build system is supported', file=sys.stderr)
            exit(1)

        app_pubspec = _process_build_commands(module, app_pubspec)

        app_module = app_module if app_module is not None else str(module['name'])
        build_path_app = f'{build_path}/{app_module}'
        build_id = len(glob.glob(f'{build_path_app}-*')) + 1
        tag, sdk_path = _process_sources(module, f'{build_path_app}-{build_id}', releases_path, no_shallow)
        _process_build_options(module, sdk_path)

        options = [f'cd {build_path} && ln -snf {app_module}-{build_id} {app_module}']
        subprocess.run(options, stdout=subprocess.PIPE, shell=True, check=True)

        return str(manifest[app_id]), app_module, app_pubspec, tag, sdk_path, build_id
    else:
        print(f'Error: No module named {app} found!', file=sys.stderr)
        print('Error: Specify the app module using the --app-module command line parameter', file=sys.stderr)
        exit(1)

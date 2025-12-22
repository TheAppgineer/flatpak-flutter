__license__ = 'MIT'
import subprocess
import yaml
import glob
import os
import shutil

from pathlib import Path
from typing import Optional, Tuple


FLUTTER_URL = 'https://github.com/flutter/flutter'


class Dumper(yaml.Dumper):
    def increase_indent(self, flow=False, *args, **kwargs):
        return super().increase_indent(flow=flow, indentless=False)


def _fetch_repos(repos: list):
    def by_path_depth(fetch_repo):
        return len(str(fetch_repo[2]).split('/'))

    repos.sort(key=by_path_depth)

    for url, ref, path, shallow, recursive in repos:
        options = ['git', 'clone']
        if shallow and recursive:
            options += ['--shallow-submodules']
        if shallow:
            options += ['--depth', '1']
        if recursive:
            options += ['--recurse-submodules']
        options += ['--branch', f"{ref}", url, path]

        try:
            subprocess.run(options, stdout=subprocess.PIPE, check=True)
        except subprocess.CalledProcessError:
            clone = 'git clone --recursive' if recursive else 'git clone'
            command = [f'{clone} {url} {path} && cd {path} && git reset --hard {ref}']
            subprocess.run(command, stdout=subprocess.PIPE, shell=True, check=True)


def _search_submodules(gitmodules):
    def get_flutter_path():
        if ('url' in submodule and 'path' in submodule and 'branch' in submodule and
                submodule['url'] == f'{FLUTTER_URL}.git' and
                submodule['branch'] == 'stable'):
            return submodule['path']

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


def _add_child_module(module, child_module):
    if 'modules' in module:
        if child_module not in module['modules']:
            module['modules'] += [child_module]
    else:
        module['modules'] = [child_module]


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


def _process_build_commands(module, app_pubspec: str):
    if 'build-commands' in module:
        insert_command = f'setup-flutter.sh -C {app_pubspec}'
        build_commands = list(module['build-commands'])

        for idx, command in enumerate(build_commands):
            if str(command).startswith('flutter pub get'):
                del build_commands[idx]
                build_commands.insert(idx, insert_command)
                break

            if 'flutter ' in str(command):
                build_commands.insert(idx, insert_command)
                break

        module['build-commands'] = build_commands


def _process_sources(module, fetch_path: str, releases_path: str, no_shallow: bool) -> Optional[str]:
    if not 'sources' in module:
        return None

    sources = module['sources']
    idxs = []
    repos = []
    tag = None

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

    _fetch_repos(repos)

    gitmodules = f'{fetch_path}/.gitmodules'

    if tag is None and os.path.isfile(gitmodules):
        sdk_path = _search_submodules(gitmodules)

        if sdk_path:
            command = [f'cd {fetch_path}/{sdk_path} && git fetch && git tag --points-at HEAD']
            result = subprocess.run(command, stdout=subprocess.PIPE, shell=True, check=True)

            if not result.returncode:
                tag = result.stdout.decode('utf-8').strip()

    _add_child_module(module, f"flutter-sdk-{tag}.json")

    for patch in glob.glob(f'{releases_path}/{tag}/*.flutter.patch'):
        shutil.copyfile(patch, Path(patch).name)

    # With the repos fetched, any patches can be applied
    for source in sources:
        if 'type' in source:
            if source['type'] == 'patch':
                if not 'path' in source:
                    continue

                dest = source['dest'] if 'dest' in source else '.'
                path = str(source['path'])

                if os.path.isdir(f'{fetch_path}/{dest}'):
                    print(f'Apply patch: {path}')
                    command = f'(cd {fetch_path}/{dest} && patch -p1) < {path}'
                    subprocess.run([command], stdout=subprocess.PIPE, shell=True, check=True)
                else:
                    print(f'Warning: Skipping patch {path}, directory {fetch_path}/{dest} does not exist')

    for idx in reversed(idxs):
        del sources[idx]

    for patch in glob.glob('*.offline.patch'):
        sources += [
            {
                'type': 'patch',
                'path': patch
            }
        ]

    module['sources'] = sources + ["pubspec-sources.json"]

    return tag, sdk_path


def fetch_flutter_app(
    manifest,
    app_module: str,
    build_path: str,
    releases_path: str,
    app_pubspec: str,
    no_shallow: bool,
) -> Tuple[str, str, Optional[str], int]:
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
            print('Error: Only the simple build system is supported')
            exit(1)

        _process_build_commands(module, app_pubspec)

        app_module = app_module if app_module is not None else str(module['name'])
        build_path_app = f'{build_path}/{app_module}'
        build_id = len(glob.glob(f'{build_path_app}-*')) + 1
        tag, sdk_path = _process_sources(module, f'{build_path_app}-{build_id}', releases_path, no_shallow)
        _process_build_options(module, sdk_path)

        options = [f'cd {build_path} && ln -snf {app_module}-{build_id} {app_module}']
        subprocess.run(options, stdout=subprocess.PIPE, shell=True, check=True)

        return str(manifest[app_id]), app_module, tag, sdk_path, build_id
    else:
        print(f'Error: No module named {app} found!')
        exit(1)

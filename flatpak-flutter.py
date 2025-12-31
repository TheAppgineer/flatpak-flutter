#!/usr/bin/env python3

__license__ = 'MIT'
import subprocess
import shutil
import argparse
import os
import sys
import yaml
import json
import urllib.parse
import urllib.request
import asyncio

from pathlib import Path
from flutter_sdk_generator.flutter_sdk_generator import generate_sdk
from flutter_app_fetcher.flutter_app_fetcher import fetch_flutter_app, add_child_module
from pubspec_generator.pubspec_generator import PUB_CACHE
from cargo_generator.cargo_generator import generate_sources as generate_cargo_sources
from pubspec_generator.pubspec_generator import generate_sources as generate_pubspec_sources
from rustup_generator.rustup_generator import generate_rustup
from packaging.version import Version

__version__ = '0.11.0'
build_path = '.flatpak-builder/build'


class Dumper(yaml.Dumper):
    def increase_indent(self, flow=False, *args, **kwargs):
        return super().increase_indent(flow=flow, indentless=False)


def _get_manifest_from_git(manifest: str, from_git: str, from_git_branch: str):
    manifest_name = Path(manifest).name
    options = [
        'git',
        'clone',
        '--depth',
        '1',
        from_git,
        f'{build_path}/{manifest_name}',
    ] if from_git_branch is None else [
        'git',
        'clone',
        '--branch',
        from_git_branch,
        '--depth',
        '1',
        from_git,
        f'{build_path}/{manifest_name}',
    ]
    manifest_path = f'{build_path}/{manifest_name}/{manifest}'

    if os.path.isfile(manifest_path):
        return_code = 0
    else:
        return_code = subprocess.run(options, stdout=subprocess.PIPE, check=True).returncode

    if return_code == 0:
        shutil.copyfile(manifest_path, manifest_name)
        shutil.rmtree(f'{build_path}/{manifest_name}')


def _fetch_flutter_app(
    manifest_path: Path,
    app_module: str,
    releases_path: str,
    app_pubspec: str,
    no_shallow: bool,
):
    if not os.path.isfile(manifest_path):
        print(f'Error: manifest file {manifest_path} not found')
        exit(1)

    with open(manifest_path, 'r') as input_stream:
        suffix = manifest_path.suffix

        if suffix == '.yml' or  suffix == '.yaml':
            manifest = yaml.full_load(input_stream)
        else:
            manifest = json.load(input_stream)

        releases_path += '/flutter'
        app_id, app_module, app_pubspec, tag, sdk_path, build_id, rust_version = fetch_flutter_app(
            manifest,
            app_module,
            build_path,
            releases_path,
            app_pubspec,
            no_shallow,
        )

        return manifest, app_id, app_module, app_pubspec, tag, sdk_path, build_id, rust_version


def _create_pub_cache(build_path_app: str, sdk_path: str, pubspec_path: str):
    full_pubspec_path = f'{build_path_app}/{pubspec_path}'

    if os.path.isfile(f'{full_pubspec_path}/pubspec.lock'):
        pub_cache = f'{os.getcwd()}/{build_path_app}/.{PUB_CACHE}'
        flutter = f'{sdk_path}/bin/flutter'
        options = f'PUB_CACHE={pub_cache} {build_path_app}/{flutter} pub get -C {full_pubspec_path}'

        subprocess.run([options], stdout=subprocess.PIPE, shell=True, check=True)
    else:
        print(f'Error: Expected to find pubspec.lock in: {pubspec_path}')
        print('       Specify path using modules.subdir or use the --app-pubspec command line parameter')
        exit(1)


def _handle_foreign_dependencies(app: str, build_path_app: str, foreign_deps_path: str):
    abs_path = f'{os.getcwd()}/{build_path_app}'
    extra_pubspecs = []
    cargo_locks = []
    sources = []
    local_deps = []

    def append_dependency(foreign_dep, pub_dev: str= ""):
        if 'extra_pubspecs' in foreign_dep:
            for pubspec in foreign_dep['extra_pubspecs']:
                extra_pubspecs.append(str(pubspec).replace('$PUB_DEV', pub_dev))

        if 'cargo_locks' in foreign_dep:
            for cargo_lock in foreign_dep['cargo_locks']:
                cargo_locks.append(str(cargo_lock).replace('$PUB_DEV', pub_dev))

        if 'manifest' in foreign_dep and 'sources' in foreign_dep['manifest']:
            for source in foreign_dep['manifest']['sources']:
                if source['type'] == 'patch':
                    dst_path = source['path']
                    src_path = f'{foreign_deps_path}/{dst_path}'

                    if os.path.isfile(src_path):
                        os.makedirs(Path(dst_path).parent, exist_ok=True)
                        shutil.copyfile(src_path, dst_path)

                if 'dest' in source:
                    dest = str(source['dest']).replace('$PUB_DEV', pub_dev)
                    dest = dest.replace('$APP', app)
                    source['dest'] = dest

                sources.append(source)

    if os.path.isfile('foreign.json'):
        with open('foreign.json') as foreign:
            foreign = json.load(foreign)
            local_deps = foreign.keys()

            for dependency in foreign.values():
                append_dependency(dependency)

    with open(f'{foreign_deps_path}/foreign_deps.json', 'r') as foreign_deps, open(f'{abs_path}/pubspec.lock') as deps:
        foreign_deps = json.load(foreign_deps)
        deps = yaml.full_load(deps)

        for name in foreign_deps.keys():
            if name not in local_deps and name in deps['packages']:
                foreign_dep = foreign_deps[name]
                foreign_dep_versions = list(foreign_dep.keys())
                dep = deps['packages'][name]
                dep_version = dep['version']

                for foreign_dep_version in reversed(foreign_dep_versions):
                    if Version(foreign_dep_version) <= Version(dep_version):
                        foreign_dep = foreign_dep[foreign_dep_version]
                        break
                else:
                    foreign_dep = foreign_dep[foreign_dep_versions[0]]

                if dep['source'] == 'hosted':
                    pub_dev = f".{PUB_CACHE}/hosted/pub.dev/{name}-{dep_version}"
                    append_dependency(foreign_dep, pub_dev)
                else:
                    print(f'Warning: Skipping foreign dependency {name}, not sourced from pub.dev')

    return extra_pubspecs, cargo_locks, sources


def _generate_pubspec_sources(app: str, app_pubspec:str, extra_pubspecs: list, foreign: list, sdk_path: str):
    flutter_tools = f'{sdk_path}/packages/flutter_tools'
    pubspec_paths = [
        f'{build_path}/{app}/{app_pubspec}/pubspec.lock',
        f'{build_path}/{app}/{flutter_tools}/pubspec.lock',
    ]

    if extra_pubspecs:
        for path in extra_pubspecs:
            pubspec_paths.append(f'{build_path}/{app}/{path}/pubspec.lock')

    pubspec_sources = generate_pubspec_sources(pubspec_paths)
    pubspec_sources += foreign

    with open('pubspec-sources.json', 'w') as out:
        json.dump(pubspec_sources, out, indent=4, sort_keys=False)
        out.write('\n')


def _generate_cargo_sources(app: str, cargo_locks: list, rust_version: str):
    if cargo_locks:
        cargo_paths = []

        for path in cargo_locks:
            cargo_paths.append(f'{build_path}/{app}/{path}/Cargo.lock')

        cargo_sources = asyncio.run(generate_cargo_sources(cargo_paths))

        with open('cargo-sources.json', 'w') as out:
            json.dump(cargo_sources, out, indent=4, sort_keys=False)
            out.write('\n')

        with open(f'rustup-{rust_version}.json', 'w') as out:
            json.dump(generate_rustup(rust_version), out, indent=4, sort_keys=False)


def _get_sdk_module(app: str, sdk_path: str, tag: str, releases: str):
    if Version(tag) < Version('3.35.0'):
        shutil.copyfile(f'{releases}/flutter/flutter-pre-3_35-shared.sh.patch', 'flutter-shared.sh.patch')
    else:
        shutil.copyfile(f'{releases}/flutter/flutter-shared.sh.patch', 'flutter-shared.sh.patch')

    if os.path.isfile(f'{releases}/flutter/{tag}/flutter-sdk.json'):
        shutil.copyfile(f'{releases}/flutter/{tag}/flutter-sdk.json', f'flutter-sdk-{tag}.json')
    else:
        generated_sdk = generate_sdk(f'{build_path}/{app}/{sdk_path}', tag)

        with open(f'flutter-sdk-{tag}.json', 'w') as out:
            json.dump(generated_sdk, out, indent=4, sort_keys=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('MANIFEST', help='Path to the manifest')
    parser.add_argument('-V', '--version', action='version', version=f'%(prog)s-{__version__}')
    parser.add_argument('--app-module', metavar='NAME', help='Name of the app module in the manifest')
    parser.add_argument('--app-pubspec', metavar='PATH', help='Path to the app pubspec')
    parser.add_argument('--extra-pubspecs', metavar='PATHS', help='Comma separated list of extra pubspec paths')
    parser.add_argument('--cargo-locks', metavar='PATHS', help='Comma separated list of Cargo.lock paths')
    parser.add_argument('--from-git', metavar='URL', required=False, help='Get input files from git repo')
    parser.add_argument('--from-git-branch', metavar='BRANCH', required=False, help='Branch to use in --from-git')
    parser.add_argument('--no-shallow-clone', action='store_true', help="Don't use shallow clones when mirroring git repos")
    parser.add_argument('--keep-build-dirs', action='store_true', help="Don't remove build directories after processing")

    args = parser.parse_args()
    manifest_path = Path(args.MANIFEST)
    raw_url = None

    if 'FLATPAK_FLUTTER_ROOT' in os.environ:
        parent = os.environ['FLATPAK_FLUTTER_ROOT']
    else:
        parent = str(Path(sys.argv[0]).parent)

    releases_path = f'{parent}/releases'
    foreign_deps_path = f'{parent}/foreign_deps'

    if args.from_git:
        url = urllib.parse.urlparse(args.from_git)

        if url.hostname == 'github.com' and args.from_git_branch is not None:
            path = str(url.path).split('.git')[0]
            raw_url = f'https://raw.githubusercontent.com{path}/{args.from_git_branch}/{args.MANIFEST}'
            urllib.request.urlretrieve(raw_url, manifest_path.name)
        else:
            _get_manifest_from_git(args.MANIFEST, args.from_git, args.from_git_branch)

    no_shallow = True if args.no_shallow_clone else False
    manifest, app_id, app_module, app_pubspec, tag, sdk_path, build_id, rust_version = _fetch_flutter_app(
        manifest_path,
        args.app_module,
        releases_path,
        args.app_pubspec,
        no_shallow,
    )
    print(f'SDK path: {sdk_path}, tag: {tag}')

    if tag is not None:
        build_path_app = f'{build_path}/{app_module}'
        _create_pub_cache(build_path_app, sdk_path, app_pubspec)

        full_pubspec_path = f'{build_path_app}/{app_pubspec}'
        extra_pubspecs, cargo_locks, foreign = _handle_foreign_dependencies(app_pubspec, full_pubspec_path, foreign_deps_path)

        if args.extra_pubspecs is not None:
            extra_pubspecs += str(args.extra_pubspecs).split(',')
        if args.cargo_locks is not None:
            cargo_locks += str(args.cargo_locks).split(',')

        _generate_pubspec_sources(app_module, app_pubspec, extra_pubspecs, foreign, sdk_path)
        _generate_cargo_sources(app_module, cargo_locks, rust_version)
        _get_sdk_module(app_module, sdk_path, tag, releases_path)

        # Write converted manifest to file
        suffix = manifest_path.suffix
        with open(f'{app_id}{suffix}', 'w') as output_stream:
            for module in manifest['modules']:
                if 'name' in module and module['name'] == app_module:
                    if len(cargo_locks):
                        module['sources'] += ['cargo-sources.json']
                        add_child_module(module, f'rustup-{rust_version}.json')

                    module['sources'] += ["pubspec-sources.json"]
                    break

            if suffix == '.json':
                json.dump(manifest, output_stream, indent=4, sort_keys=False)
            else:
                source = raw_url if raw_url is not None else manifest_path
                prepend = f'''# Generated by flatpak-flutter v{__version__} from {source}, do not edit
# Visit the project at https://github.com/TheAppgineer/flatpak-flutter
'''
                output_stream.write(prepend)
                yaml.dump(data=manifest, stream=output_stream, indent=2, sort_keys=False, Dumper=Dumper)

        if not args.keep_build_dirs:
            shutil.rmtree(f'{build_path}/{app_module}-{build_id}')
            os.remove(f'{build_path}/{app_module}')


if __name__ == '__main__':
    main()

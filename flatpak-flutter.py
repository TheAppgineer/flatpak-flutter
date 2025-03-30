#!/usr/bin/env python3

__license__ = 'MIT'
import subprocess
import shutil
import argparse
import os
import yaml
import json

from pathlib import Path
from flutter_sdk_generator.flutter_sdk_generator import generate_sdk
from offline_manifest_generator.offline_manifest_generator import convert_to_offline
from pubspec_generator.pubspec_generator import generate_sources

__version__ = '0.4.0'
build_path = '.flatpak-builder/build'


class Dumper(yaml.Dumper):
    def increase_indent(self, flow=False, *args, **kwargs):
        return super().increase_indent(flow=flow, indentless=False)


def _get_manifest_from_git(manifest: str, from_git: str, from_git_branch: str):
    options = [
        'git',
        'clone',
        '--branch',
        from_git_branch,
        '--depth',
        '1',
        from_git,
        f'{build_path}/{manifest}',
    ]
    manifest_path = f'{build_path}/{manifest}/{manifest}'

    if os.path.isfile(manifest_path):
        return_code = 0
    else:
        return_code = subprocess.run(options, stdout=subprocess.PIPE, check=True).returncode

    if return_code == 0:
        shutil.copyfile(manifest_path, manifest)


def _perform_online_build(args):
    print('Starting online build...')
    options = [
        'flatpak',
        'run',
        'org.flatpak.Builder',
        '--force-clean',
        '--user',
        '--install-deps-from=flathub',
        '--build-only',
        '--keep-build-dirs',
        args.DIRECTORY,
        args.MANIFEST,
    ]

    return subprocess.run(options, stdout=subprocess.PIPE, check=True).returncode


def _generate_offline_manifest(manifest_path: str):
    with open(manifest_path, 'r') as input_stream:
        suffix = (Path(manifest_path).suffix)

        if suffix == '.yml' or  suffix == '.yaml':
            manifest = yaml.full_load(input_stream)
        else:
            manifest = json.load(input_stream)

        app_id, tag = convert_to_offline(manifest)

        # Write converted manifest to file
        with open(f'{app_id}{suffix}', 'w') as output_stream:
            if suffix == '.json':
                json.dump(manifest, output_stream, indent=4, sort_keys=False)
            else:
                prepend = f'''# Generated from {manifest_path}, do not edit
# Visit the flatpak-flutter project at https://github.com/TheAppgineer/flatpak-flutter
'''
                output_stream.write(prepend)
                yaml.dump(data=manifest, stream=output_stream, indent=2, sort_keys=False, Dumper=Dumper)

        return app_id, tag


def _generate_pubspec_sources(app: str, extra_pubspec: str):
    pubspec_paths = [
        f'{build_path}/{app}/pubspec.lock',
        f'{build_path}/{app}/flutter/packages/flutter_tools/pubspec.lock',
    ]

    if extra_pubspec:
        paths = extra_pubspec.split(',')
        for path in paths:
            pubspec_paths.append(f'{build_path}/{app}/{path}')

    pubspec_sources = []
    deduped = 0

    for path in pubspec_paths:
        generated_sources = generate_sources(path)

        if len(pubspec_sources) == 0:
            pubspec_sources = generated_sources
        else:
            for source in generated_sources:
                if not source in pubspec_sources:
                    pubspec_sources.append(source)
                else:
                    deduped += 1

            print(f'Deduped {deduped} packages')

    with open('pubspec-sources.json', 'w') as out:
        json.dump(pubspec_sources, out, indent=4, sort_keys=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('DIRECTORY', help='Path to the build directory')
    parser.add_argument('MANIFEST', help='Path to the manifest')
    parser.add_argument('-V', '--version', action='version', version=f'%(prog)s-{__version__}')
    parser.add_argument('--extra-pubspec', metavar='PATHS', help='Comma separated list of extra pubspec files')
    parser.add_argument('--from-git', metavar='URL', required=False, help='Get input files from git repo')
    parser.add_argument('--from-git-branch', metavar='BRANCH', required=False, help='Branch to use in --from-git')
    args = parser.parse_args()

    if args.from_git:
        _get_manifest_from_git(args.MANIFEST, args.from_git, args.from_git_branch)

    _perform_online_build(args)

    app_id, tag = _generate_offline_manifest(args.MANIFEST)
    print(app_id, tag)

    app = app_id.split('.')[-1:][0]
    _generate_pubspec_sources(app, args.extra_pubspec)
    shutil.copyfile(f'{build_path}/{app}/flutter/packages/flutter_tools/.dart_tool/package_config.json', 'package_config.json')

    generated_sdk = generate_sdk(f'{build_path}/{app}/flutter')

    with open(f'flutter-sdk-{tag}.json', 'w') as out:
        json.dump(generated_sdk, out, indent=4, sort_keys=False)


if __name__ == '__main__':
    main()

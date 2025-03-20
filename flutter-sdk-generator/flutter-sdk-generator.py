#!/usr/bin/env python3

__license__ = 'MIT'
import json
import subprocess
import argparse
import logging
from typing import Any, Dict, List


_FlatpakSourceType = Dict[str, Any]


def get_sha256(url: str) -> str:
    print(f'Getting sha256 of {url}...')
    stdout = subprocess.run([f'curl -s {url} | sha256sum'], stdout=subprocess.PIPE, shell=True, check=True).stdout

    return stdout.decode('utf-8').split(' ')[0]


def get_commit(sdk_path: str) -> str:
    stdout = subprocess.run([f'git -C {sdk_path} rev-parse HEAD'], stdout=subprocess.PIPE, shell=True, check=True).stdout

    return stdout.decode('utf-8').strip()


def generate_sdk(
    sdk_path: str,
) -> List[_FlatpakSourceType]:
    sdk_version = open(f'{sdk_path}/version', 'r').readline().strip()
    sdk_commit = get_commit(sdk_path)
    engine = open(f'{sdk_path}/bin/internal/engine.version', 'r').readline().strip()
    gradle_wrapper = open(f'{sdk_path}/bin/internal/gradle_wrapper.version', 'r').readline().strip()
    material_fonts = open(f'{sdk_path}/bin/internal/material_fonts.version', 'r').readline().strip()

    engine = f'https://storage.googleapis.com/flutter_infra_release/flutter/{engine}'
    material_fonts = f'https://storage.googleapis.com/{material_fonts}'
    gradle_wrapper = f'https://storage.googleapis.com/{gradle_wrapper}'

    dart_sdk_x64 = f'{engine}/dart-sdk-linux-x64.zip'
    dart_sdk_arm64 = f'{engine}/dart-sdk-linux-arm64.zip'
    sky_engine = f'{engine}/sky_engine.zip'
    flutter_gpu = f'{engine}/flutter_gpu.zip'
    flutter_patched_sdk = f'{engine}/flutter_patched_sdk.zip'
    flutter_patched_sdk_product = f'{engine}/flutter_patched_sdk_product.zip'
    artifacts_x64 = f'{engine}/linux-x64/artifacts.zip'
    font_subset_x64 = f'{engine}/linux-x64/font-subset.zip'
    flutter_gtk_x64_profile = f'{engine}/linux-x64-profile/linux-x64-flutter-gtk.zip'
    flutter_gtk_x64_release = f'{engine}/linux-x64-release/linux-x64-flutter-gtk.zip'
    artifacts_arm64 = f'{engine}/linux-arm64/artifacts.zip'
    font_subset_arm64 = f'{engine}/linux-arm64/font-subset.zip'
    flutter_gtk_arm64_profile = f'{engine}/linux-arm64-profile/linux-arm64-flutter-gtk.zip'
    flutter_gtk_arm64_release = f'{engine}/linux-arm64-release/linux-arm64-flutter-gtk.zip'

    return {
        'name': 'flutter',
        'buildsystem': 'simple',
        'build-commands': [
            'cp flutter/bin/internal/engine.version flutter/bin/cache/engine-dart-sdk.stamp',
            'cp flutter/bin/internal/material_fonts.version flutter/bin/cache/material_fonts.stamp',
            'cp flutter/bin/internal/gradle_wrapper.version flutter/bin/cache/gradle_wrapper.stamp',
            'cp flutter/bin/internal/engine.version flutter/bin/cache/flutter_sdk.stamp',
            'cp flutter/bin/internal/engine.version flutter/bin/cache/font-subset.stamp',
            'cp flutter/bin/internal/engine.version flutter/bin/cache/linux-sdk.stamp',
            './setup-links.sh',
            'mkdir -p /var/lib && cp -r flutter /var/lib'
        ],
        'sources': [
        {
            'type': 'git',
            'url': 'https://github.com/flutter/flutter.git',
            'tag': sdk_version,
            'commit': sdk_commit,
            'dest': 'flutter'
        },
        {
            'type': 'archive',
            'only-arches': [
                'x86_64'
            ],
            'url': dart_sdk_x64,
            'sha256': get_sha256(dart_sdk_x64),
            'strip-components': 0,
            'dest': 'flutter/bin/cache'
        },
        {
            'type': 'archive',
            'only-arches': [
                'aarch64'
            ],
            'url': dart_sdk_arm64,
            'sha256': get_sha256(dart_sdk_arm64),
            'strip-components': 0,
            'dest': 'flutter/bin/cache'
        },
        {
            'type': 'archive',
            'url': material_fonts,
            'sha256': get_sha256(material_fonts),
            'dest': 'flutter/bin/cache/artifacts/material_fonts'
        },
        {
            'type': 'archive',
            'url': gradle_wrapper,
            'sha256': get_sha256(gradle_wrapper),
            'strip-components': 0,
            'dest': 'flutter/bin/cache/artifacts/gradle_wrapper'
        },
        {
            'type': 'archive',
            'url': sky_engine,
            'sha256': get_sha256(sky_engine),
            'dest': 'flutter/bin/cache/pkg/sky_engine'
        },
        {
            'type': 'archive',
            'url': flutter_gpu,
            'sha256': get_sha256(flutter_gpu),
            'dest': 'flutter/bin/cache/pkg/flutter_gpu'
        },
        {
            'type': 'archive',
            'url': flutter_patched_sdk,
            'sha256': get_sha256(flutter_patched_sdk),
            'dest': 'flutter/bin/cache/artifacts/engine/common/flutter_patched_sdk'
        },
        {
            'type': 'archive',
            'url': flutter_patched_sdk_product,
            'sha256': get_sha256(flutter_patched_sdk_product),
            'dest': 'flutter/bin/cache/artifacts/engine/common/flutter_patched_sdk_product'
        },
        {
            'type': 'archive',
            'only-arches': [
                'x86_64'
            ],
            'url': artifacts_x64,
            'sha256': get_sha256(artifacts_x64),
            'strip-components': 0,
            'dest': 'flutter/bin/cache/artifacts/engine/linux-x64'
        },
        {
            'type': 'archive',
            'only-arches': [
                'x86_64'
            ],
            'url': font_subset_x64,
            'sha256': get_sha256(font_subset_x64),
            'dest': 'flutter/bin/cache/artifacts/engine/linux-x64'
        },
        {
            'type': 'archive',
            'only-arches': [
                'x86_64'
            ],
            'url': flutter_gtk_x64_profile,
            'sha256': get_sha256(flutter_gtk_x64_profile),
            'strip-components': 0,
            'dest': 'flutter/bin/cache/artifacts/engine/linux-x64-profile'
        },
        {
            'type': 'archive',
            'only-arches': [
                'x86_64'
            ],
            'url': flutter_gtk_x64_release,
            'sha256': get_sha256(flutter_gtk_x64_release),
            'strip-components': 0,
            'dest': 'flutter/bin/cache/artifacts/engine/linux-x64-release'
        },
        {
            'type': 'archive',
            'only-arches': [
                'aarch64'
            ],
            'url': artifacts_arm64,
            'sha256': get_sha256(artifacts_arm64),
            'strip-components': 0,
            'dest': 'flutter/bin/cache/artifacts/engine/linux-arm64'
        },
        {
            'type': 'archive',
            'only-arches': [
                'aarch64'
            ],
            'url': font_subset_arm64,
            'sha256': get_sha256(font_subset_arm64),
            'dest': 'flutter/bin/cache/artifacts/engine/linux-arm64'
        },
        {
            'type': 'archive',
            'only-arches': [
                'aarch64'
            ],
            'url': flutter_gtk_arm64_profile,
            'sha256': get_sha256(flutter_gtk_arm64_profile),
            'strip-components': 0,
            'dest': 'flutter/bin/cache/artifacts/engine/linux-arm64-profile'
        },
        {
            'type': 'archive',
            'only-arches': [
                'aarch64'
            ],
            'url': flutter_gtk_arm64_release,
            'sha256': get_sha256(flutter_gtk_arm64_release),
            'strip-components': 0,
            'dest': 'flutter/bin/cache/artifacts/engine/linux-arm64-release'
        },
        {
            'type': 'patch',
            'path': 'flutter-shared.sh.patch'
        },
        {
            'type': 'script',
            'dest': 'flutter/bin',
            'dest-filename': 'setup-flutter.sh',
            'commands': [
                'mkdir -p flutter/bin && cp -r /var/lib/flutter/bin/cache-base flutter/bin/cache',
                'flutter pub get --offline'
            ]
        },
        {
            'type': 'script',
            'dest-filename': 'setup-links.sh',
            'commands': [
                'mv flutter/bin/cache{,-base}',
                'APP=$(IFS=\".\" && read -ra array <<< $FLATPAK_ID && echo ${array[-1]})',
                'ln -s /run/build/$APP/flutter/bin/cache flutter/bin/cache',
                'ln -s /run/build/$APP/flutter/packages/flutter_tools/.dart_tool flutter/packages/flutter_tools/.dart_tool'
            ]
        }
    ]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('sdk_path', help='Path to the Flutter SDK')
    parser.add_argument('-o', '--output', required=False, help='Where to write generated sources')
    parser.add_argument('-d', '--debug', action='store_true')
    args = parser.parse_args()
    if args.output is not None:
        outfile = args.output
    else:
        outfile = 'flutter-sdk.json'
    if args.debug:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.INFO
    logging.basicConfig(level=loglevel)
    generated_sdk = generate_sdk(args.sdk_path)

    with open(outfile, 'w') as out:
        json.dump(generated_sdk, out, indent=4, sort_keys=False)


if __name__ == '__main__':
    main()

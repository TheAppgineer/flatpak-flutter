#!/usr/bin/env python3

# Read about the pub cache: https://dart.googlesource.com/pub.git/+/1d7b0d9a/doc/cache_layout.md

__license__ = 'MIT'
import json
import argparse
import hashlib
import asyncio
from typing import Any, Dict, List, Optional

import yaml

PUB_DEV = 'https://pub.dev/api/archives'
PUB_CACHE = 'pub-cache'
GIT_CACHE = f'.{PUB_CACHE}/git/cache'


_FlatpakSourceType = Dict[str, Any]


def get_git_package_sources(
    package: Any,
) -> List[_FlatpakSourceType]:
    repo_url = str(package['description']['url'])
    split = repo_url.split('/')
    name = split[len(split) - 1].split('.git')[0]
    commit = package['description']['resolved-ref']
    assert commit, 'The commit needs to be indicated in the description'
    dest = f'.{PUB_CACHE}/git/{name}-{commit}'

    sha1 = hashlib.sha1()
    sha1.update(repo_url.encode('utf-8'))

    cache_path = f'{GIT_CACHE}/{name}-{sha1.hexdigest()}'
    commands = [
        f'mkdir -p {cache_path}',
        f'cp -rf {dest}/.git/* {cache_path}'
    ]

    git_sources: List[_FlatpakSourceType] = [
        {
            'type': 'git',
            'url': repo_url,
            'commit': commit,
            'dest': dest,
        },
        {
            'type': 'shell',
            'commands': commands,
        },
    ]

    return git_sources


async def get_package_sources(
    name: str,
    package: Any,
) -> Optional[List[_FlatpakSourceType]]:
    version = package['version']

    if 'source' not in package:
        print(f'{package} has no source')
        return None
    source = package['source']

    if source == 'git':
        return get_git_package_sources(package)

    if source != 'hosted':
        return None

    if 'sha256' in package['description']:
        sha256 = package['description']['sha256']
    else:
        print(f'No sha256 in description of {name}')
        return None

    # TODO: Buildup .pub-cache/hosted/pub.dev/.cache
    # fetch releases using: https://pub.dev/api/packages/_fe_analyzer_shared
    # turns out be non-critical for offline pub use

    pubdev_sources = [
        {
            'type': 'archive',
            'archive-type': 'tar-gzip',
            'url': f'{PUB_DEV}/{name}-{version}.tar.gz',
            'sha256': sha256,
            'strip-components': 0,
            'dest': f'.{PUB_CACHE}/hosted/pub.dev/{name}-{version}',
        },
        {
            'type': 'inline',
            'contents': sha256,
            'dest': f'.{PUB_CACHE}/hosted-hashes/pub.dev',
            'dest-filename': f'{name}-{version}.sha256',
        },
    ]
    return pubdev_sources


async def generate_sources(
    pubspec_lock: Any,
) -> List[_FlatpakSourceType]:
    sources: List[_FlatpakSourceType] = []
    package_sources = []

    pkg_coros = [get_package_sources(name, pubspec_lock['packages'][name]) for name in pubspec_lock['packages']]
    for pkg in await asyncio.gather(*pkg_coros):
        if pkg is None:
            continue
        else:
            pkg_sources = pkg
        package_sources.extend(pkg_sources)

    sources.extend(package_sources)

    return sources


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('pubspec_lock', help='Path to the pubspec.lock file')
    parser.add_argument('-o', '--output', required=False, help='Where to write generated sources')
    parser.add_argument('-a', '--append', action='store_true')
    args = parser.parse_args()

    if args.output is not None:
        outfile = args.output
    else:
        outfile = 'pubspec-sources.json'

    stream = open(args.pubspec_lock, 'r')
    pubspec_lock = yaml.load(stream, Loader=yaml.FullLoader)
    generated_sources = asyncio.run(generate_sources(pubspec_lock))

    if args.append:
        with open(outfile, 'r') as current:
            current_sources = list(json.load(current))
            deduped = 0

            for source in generated_sources:
                if not source in current_sources:
                    current_sources.append(source)
                else:
                    deduped += 1

            print(f'Deduped {deduped} packages')
            generated_sources = current_sources

    with open(outfile, 'w') as out:
        json.dump(generated_sources, out, indent=4, sort_keys=False)


if __name__ == '__main__':
    main()

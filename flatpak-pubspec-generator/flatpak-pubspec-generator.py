#!/usr/bin/env python3

# Read about the pub cache: https://dart.googlesource.com/pub.git/+/1d7b0d9a/doc/cache_layout.md

__license__ = 'MIT'
import json
import os
import subprocess
import argparse
import logging
import hashlib
import asyncio
from typing import Any, Dict, List, NamedTuple, Optional, Tuple, TypedDict

import yaml

PUB_DEV = 'https://pub.dev/api/archives'
PUB_CACHE = 'pub-cache'
GIT_CACHE = f'{PUB_CACHE}/git/cache'


_FlatpakSourceType = Dict[str, Any]


def fetch_bare_git_repo(git_url: str, commit: str, clone_dir: str):
    if not os.path.isfile(os.path.join(clone_dir, 'HEAD')):
        subprocess.run(['git', 'clone', '--bare', git_url, clone_dir], check=True)


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
    fetch_bare_git_repo(repo_url, commit, cache_path)

    git_sources: List[_FlatpakSourceType] = [
        {
            'type': 'git',
            'url': repo_url,
            'commit': commit,
            'dest': dest,
        }
    ]

    return git_sources


async def get_package_sources(
    name: str,
    package: Any,
) -> Optional[List[_FlatpakSourceType]]:
    version = package['version']

    if 'source' not in package:
        logging.debug('%s has no source', package)
        return None
    source = package['source']

    if source == 'git':
        return get_git_package_sources(package)

    if source != 'hosted':
        return None

    if 'sha256' in package['description']:
        sha256 = package['description']['sha256']
    else:
        logging.warning(f'No sha256 in description of {name}')
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

    if os.path.isdir(GIT_CACHE):
        print('create git cache archive')
        subprocess.run(['tar', 'czf', 'pub-git-cache.tar.gz', GIT_CACHE], check=True)

        package_sources.extend([
            {
                'type': 'archive',
                'archive-type': 'tar-gzip',
                'path': 'pub-git-cache.tar.gz',
                'dest': f'.{PUB_CACHE}',
            }
        ])

    sources.extend(package_sources)

    return sources


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('pubspec_lock', help='Path to the pubspec.lock file')
    parser.add_argument('-o', '--output', required=False, help='Where to write generated sources')
    parser.add_argument('-d', '--debug', action='store_true')
    args = parser.parse_args()
    if args.output is not None:
        outfile = args.output
    else:
        outfile = 'generated-sources.json'
    if args.debug:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.INFO
    logging.basicConfig(level=loglevel)

    stream = open(args.pubspec_lock, 'r')
    pubspec_lock = yaml.load(stream, Loader=yaml.FullLoader)
    generated_sources = asyncio.run(generate_sources(pubspec_lock))

    with open(outfile, 'w') as out:
        json.dump(generated_sources, out, indent=4, sort_keys=False)


if __name__ == '__main__':
    main()

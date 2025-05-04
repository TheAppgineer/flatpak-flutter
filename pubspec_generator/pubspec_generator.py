#!/usr/bin/env python3

# Read about the pub cache: https://dart.googlesource.com/pub.git/+/1d7b0d9a/doc/cache_layout.md

__license__ = 'MIT'
import argparse
import hashlib
import json
import yaml

from typing import Any, Dict, List, Optional

PUB_DEV = 'https://pub.dev/api/archives'
PUB_CACHE = 'pub-cache'
GIT_CACHE = f'.{PUB_CACHE}/git/cache'


_FlatpakSourceType = Dict[str, Any]


def _get_git_package_sources(
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


def _get_package_sources(
    name: str,
    package: Any,
) -> Optional[List[_FlatpakSourceType]]:
    version = package['version']

    if 'source' not in package:
        print(f'{package} has no source')
        return None
    source = package['source']

    if source == 'git':
        return _get_git_package_sources(package)

    if source != 'hosted':
        return None

    if 'sha256' in package['description']:
        sha256 = package['description']['sha256']
    else:
        print(f'No sha256 in description of {name}')
        return None

    sources = [
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

    return sources


def generate_sources(
    pubspec_paths: List[str],
) -> List[_FlatpakSourceType]:
    pubspec_sources = []
    deduped = 0

    for path in pubspec_paths:
        stream = open(path, 'r')
        pubspec_lock = yaml.load(stream, Loader=yaml.FullLoader)

        for name in pubspec_lock['packages']:
            sources = _get_package_sources(name, pubspec_lock['packages'][name])

            if sources is not None:
                for source in sources:
                    if source in pubspec_sources:
                        deduped += 1
                    else:
                        pubspec_sources.append(source)

    print(f'Deduped {deduped} packages')

    return pubspec_sources


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('pubspec_paths', help='Comma separated list of paths to pubspec.lock files')
    parser.add_argument('-o', '--output', required=False, help='Where to write generated sources')
    args = parser.parse_args()

    if args.output is not None:
        outfile = args.output
    else:
        outfile = 'pubspec-sources.json'

    pubspec_paths = str(args.pubspec_paths).split(',')
    pubspec_sources = generate_sources(pubspec_paths)

    with open(outfile, 'w') as out:
        json.dump(pubspec_sources, out, indent=4, sort_keys=False)
        out.write('\n')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3

# Read about the pub cache: https://dart.googlesource.com/pub.git/+/1d7b0d9a/doc/cache_layout.md

__license__ = 'MIT'
import argparse
import datetime
import hashlib
import json
import sys
import yaml

from typing import Any, Dict, List, Optional, Tuple
from urllib.request import urlopen

PUB_DEV = 'https://pub.dev/api/archives'
PUB_CACHE = 'pub-cache'
GIT_CACHE = f'.{PUB_CACHE}/git/cache'


_FlatpakSourceType = Dict[str, Any]
_PubConfigType = Dict[str, Any]


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
) -> Optional[Tuple[List[_FlatpakSourceType], _PubConfigType]]:
    version = package['version']

    if 'source' not in package:
        print(f'{package} has no source')
        return None
    source = package['source']

    if source == 'git':
        return _get_git_package_sources(package), { 'name': name }

    if source != 'hosted':
        return None

    if 'sha256' in package['description']:
        sha256 = package['description']['sha256']
    else:
        print(f'No sha256 in description of {name}')
        return None

    releases_url = f'https://pub.dev/api/packages/{name}'
    releases = list(json.load(urlopen(releases_url))['versions'])
    releases.reverse()

    for release in releases:
        if release['version'] == version:
            sdk = str(release['pubspec']['environment']['sdk']).split(' ')[0]
            for char in '>=^':
                sdk = sdk.replace(char, '')
            sdk_version = '.'.join(sdk.split('.')[:2])
            break

    dest_hosted = f'.{PUB_CACHE}/hosted/pub.dev/{name}-{version}'
    sources = [
        {
            'type': 'archive',
            'archive-type': 'tar-gzip',
            'url': f'{PUB_DEV}/{name}-{version}.tar.gz',
            'sha256': sha256,
            'strip-components': 0,
            'dest': dest_hosted,
        },
        {
            'type': 'inline',
            'contents': sha256,
            'dest': f'.{PUB_CACHE}/hosted-hashes/pub.dev',
            'dest-filename': f'{name}-{version}.sha256',
        },
    ]
    config = {
        'name': name,
        'rootUri': f'file://./{dest_hosted}',
        'packageUri': 'lib/',
        'languageVersion': sdk_version,
    }

    return sources, config


def generate_sources(
    pubspec_paths: List[str],
    generator_version: str
) -> Tuple[List[_FlatpakSourceType], _PubConfigType]:
    pubspec_sources = []
    pubspec_configs = []
    deduped = 0

    for path in pubspec_paths:
        stream = open(path, 'r')
        pubspec_lock = yaml.load(stream, Loader=yaml.FullLoader)
        sources: List[_FlatpakSourceType] = []
        configs: List[_PubConfigType] = []

        for name in pubspec_lock['packages']:
            sources_configs = _get_package_sources(name, pubspec_lock['packages'][name])

            if sources_configs is not None:
                sources.extend(sources_configs[0])
                configs.append(sources_configs[1])

        if len(pubspec_sources) == 0:
            pubspec_sources = sources
            pubspec_configs = configs
        else:
            for source in sources:
                if not source in pubspec_sources:
                    pubspec_sources.append(source)
                else:
                    deduped += 1

            for config in configs:
                if not config in pubspec_configs:
                    pubspec_configs.append(config)

            print(f'Deduped {deduped} packages')

    def by_name(config):
        return config['name']

    pubspec_configs.sort(key=by_name)
    package_config = {
        'configVersion': 2,
        'packages': pubspec_configs,
        'generated': datetime.datetime.now().isoformat(),
        'generator': sys.argv[0].split('/')[-1:][0],
        'generatorVersion': generator_version,
        'pubCache': f'file://./.{PUB_CACHE}',
    }

    return pubspec_sources, package_config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('pubspec_paths', help='Path to the pubspec.lock file')
    parser.add_argument('-o', '--output', required=False, help='Where to write generated sources')
    parser.add_argument('-g', '--generator_version', action='store_true')
    args = parser.parse_args()

    if args.output is not None:
        outfile = args.output
    else:
        outfile = 'pubspec-sources.json'

    pubspec_paths = str(args.pubspec_paths).split(',')
    pubspec_sources, package_config = generate_sources(pubspec_paths, args.generator_version)

    with open(outfile, 'w') as out:
        json.dump(pubspec_sources, out, indent=4, sort_keys=False)
        out.write('\n')

    with open('package_config.json', 'w') as out:
        json.dump(package_config, out, indent=2, sort_keys=False)
        out.write('\n')


if __name__ == '__main__':
    main()

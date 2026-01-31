#!/usr/bin/env python3

__license__ = 'MIT'
import hashlib
import json
import sys
import tomlkit
import urllib.request


def _get_rustup_channel_entries(url: str):
    url_sha256 = f'{url}.sha256'

    with urllib.request.urlopen(url_sha256) as response:
        sha256 = hashlib.sha256()
        data = response.read()
        sha256.update(data)
        toml_sha256 = data.decode('utf-8').split(' ')[0]

        return [
            {
                'type': 'file',
                'url': url,
                'sha256': toml_sha256,
                'dest': 'static.rust-lang.org/dist'
            },
            {
                'type': 'file',
                'url': url_sha256,
                'sha256': sha256.hexdigest(),
                'dest': 'static.rust-lang.org/dist'
            }
        ]


def _get_rustup_init_entry(arch: str):
    triplet = f'{arch}-unknown-linux-gnu'
    url = f'https://static.rust-lang.org/rustup/dist/{triplet}/rustup-init'

    with urllib.request.urlopen(f'{url}.sha256') as response:
        data = response.read()
        sha256 = data.decode('utf-8').split(' ')[0]

        return {
            'type': 'file',
            'only-arches': [
                arch
            ],
            'url': url,
            'sha256': sha256,
        }


def _generate_sources(version: str):
    packages = ['cargo', 'rust-std', 'rustc']
    arches = ['aarch64', 'x86_64']
    url = f'https://static.rust-lang.org/dist/channel-rust-{version}.toml'

    with urllib.request.urlopen(url) as response:
        data = response.read().decode('utf-8')
        stable = tomlkit.loads(data)
        date = stable['date']
        pkgs = stable['pkg']
        sources = _get_rustup_channel_entries(url)

        for arch in arches:
            sources.append(_get_rustup_init_entry(arch))

        for package in packages:
            if package not in pkgs:
                continue

            targets = pkgs[package]['target']

            for arch in arches:
                triplet = f'{arch}-unknown-linux-gnu'

                if triplet not in targets:
                    continue

                details = targets[triplet]
                sources.append(
                    {
                        'type': 'file',
                        'only-arches': [
                            arch
                        ],
                        'url': details['xz_url'],
                        'sha256': details['xz_hash'],
                        'dest': f'static.rust-lang.org/dist/{date}'
                    }
                )

        return sources


def generate_rustup(version: str, rustup_path: str):
    return {
        'name': 'rustup',
        'buildsystem': 'simple',
        'build-options': {
            'env': {
                'CARGO_HOME': rustup_path,
                'RUSTUP_HOME': rustup_path,
                'RUSTUP_DIST_SERVER': 'file:///run/build/rustup/static.rust-lang.org'
            }
        },
        'build-commands': [
            f'chmod +x rustup-init && ./rustup-init -y --default-toolchain {version} --profile minimal --no-modify-path',
            f'ln -s {rustup_path}/toolchains/{version}-${{FLATPAK_ARCH}}-unknown-linux-gnu {rustup_path}/toolchains/stable-${{FLATPAK_ARCH}}-unknown-linux-gnu'
        ],
        'sources': _generate_sources(version)
    }


def main():
    if len(sys.argv) < 3:
        print(f'Usage: {sys.argv[0]} <Rust version> <rustup path>')
        exit(1)

    version = sys.argv[1]
    rustup_path = sys.argv[2]

    with open(f'rustup-{version}.json', 'w') as out:
        json.dump(generate_rustup(version, rustup_path), out, indent=4, sort_keys=False)


if __name__ == '__main__':
    main()

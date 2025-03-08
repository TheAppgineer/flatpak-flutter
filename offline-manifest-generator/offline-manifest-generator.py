__license__ = 'MIT'
import argparse
import yaml
import json
import glob
from pathlib import Path


FLUTTER_URL = 'https://github.com/flutter/flutter.git'


class Dumper(yaml.Dumper):
    def increase_indent(self, flow=False, *args, **kwargs):
        return super().increase_indent(flow=flow, indentless=False)


def process_build_options(module):
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
                if path.endswith('flutter/bin'):
                    del paths[idx]
                    paths.insert(idx, '/var/lib/flutter/bin')
                    build_options['append-path'] = ':'.join(paths)
                    break


def process_build_commands(module):
    if 'build-commands' in module:
        insert_commands = ['mkdir -p build/native_assets/linux', 'setup-flutter.sh']
        build_commands = list(module['build-commands'])

        for (idx, command) in enumerate(build_commands):
            if str(command).startswith('flutter pub get'):
                del build_commands[idx]
                for command in reversed(insert_commands):
                    build_commands.insert(idx, command)
                break

            if str(command).startswith('flutter build linux'):
                for command in reversed(insert_commands):
                    build_commands.insert(idx, command)
                break

        module['build-commands'] = build_commands


def process_sources(module):
    if not 'sources' in module:
        return

    sources = module['sources']

    idxs = []
    for (idx, source) in enumerate(sources):
        if 'type' in source:
            if source['type'] == 'git':
                if not 'url' in source or not 'tag' in source:
                    continue

                if source['url'] == FLUTTER_URL:
                    idxs.append(idx)
                    if 'modules' in module:
                        module['modules'] += [f"flutter-sdk-{source['tag']}.json"]
                    else:
                        module['modules'] = [f"flutter-sdk-{source['tag']}.json"]
                    print(source['tag'])

            if source['type'] == 'patch' and '.flutter.patch' in str(source['path']):
                idxs.append(idx)

    for idx in reversed(idxs):
        del sources[idx]

    sources += [
        {
            'type': 'file',
            'path': 'package_config.json',
            'dest': 'flutter/packages/flutter_tools/.dart_tool'
        }
    ]

    for patch in glob.glob('*.offline.patch'):
        sources += [
            {
                'type': 'patch',
                'path': patch
            }
        ]

    sources += glob.glob("pubspec-sources*.json")


def convert_to_offline(manifest) -> str:
    if 'app-id' in manifest:
        id = 'app-id'
    elif 'id' in manifest:
        id = 'id'
    else:
        exit(1)

    app_id = str(manifest[id]).split('.')
    app = app_id[len(app_id) - 1]

    if not 'modules' in manifest:
        exit(1)

    for module in manifest['modules']:
        if not 'name' in module or module['name'] != app:
            continue

        if not 'buildsystem' in module or module['buildsystem'] != 'simple':
            print('Currently only the simple build system is supported')
            exit(1)

        process_build_options(module)
        process_build_commands(module)
        process_sources(module)

        break

    return manifest[id]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('flatpak_manifest', help='The Flatpak manifest file')
    args = parser.parse_args()
    suffix = (Path(args.flatpak_manifest).suffix)

    with open(args.flatpak_manifest, 'r') as input_stream:
        if suffix == '.yml':
            manifest = yaml.full_load(input_stream)
        else:
            manifest = json.load(input_stream)

    app_id = convert_to_offline(manifest)

    if suffix == '.yml':
        with open(f'{app_id}.yml', 'w') as output_stream:
            prepend = f'''# Generated from {args.flatpak_manifest}, do not edit
# Visit the flatpak-flutter project at https://github.com/TheAppgineer/flatpak-flutter
'''
            output_stream.write(prepend)
            yaml.dump(data=manifest, stream=output_stream, indent=2, sort_keys=False, Dumper=Dumper)
    else:
        with open(f'{app_id}.json', 'w') as output_stream:
            json.dump(manifest, output_stream, indent=4, sort_keys=False)

if __name__ == '__main__':
    main()

FROM python:3.8-slim

WORKDIR /usr/src/app

RUN apt-get update && DEBIAN_FRONTEND=noninteractive \
    apt-get install -y --no-install-recommends curl git unzip

RUN pip install --no-cache-dir packaging pyyaml tomlkit

COPY flatpak-flutter.py ./flatpak-flutter
COPY cargo_generator/cargo_generator.py ./cargo_generator/
COPY flutter_app_fetcher/flutter_app_fetcher.py ./flutter_app_fetcher/
COPY flutter_sdk_generator/flutter_sdk_generator.py ./flutter_sdk_generator/
COPY pubspec_generator/pubspec_generator.py ./pubspec_generator/
COPY rustup_generator/rustup_generator.py ./rustup_generator/
COPY git_actions/git_actions.py ./git_actions
COPY foreign_deps ./foreign_deps
COPY releases ./releases/

WORKDIR /usr/src/flatpak
ENV HOME=/usr/src/flatpak/.flatpak-builder
ENTRYPOINT [ "/usr/src/app/flatpak-flutter" ]

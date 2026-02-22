import subprocess

from packaging.version import Version


def _get_git_version() -> Version:
    result = subprocess.run(['git', '--version'], stdout=subprocess.PIPE, check=True)

    # output: git version <version>
    return Version(result.stdout.decode('utf-8').strip().split(' ')[2])


def fetch_repos(repos: list):
    def by_path_depth(fetch_repo):
        return len(str(fetch_repo[2]).split('/'))

    repos.sort(key=by_path_depth)

    for url, ref, path, shallow, recursive in repos:
        options = ['git', 'clone', '-c', 'advice.detachedHead=false']
        if shallow and recursive:
            options += ['--shallow-submodules']
        if shallow:
            options += ['--depth', '1']
        if recursive:
            options += ['--recurse-submodules']
        if ref:
            options += ['--branch', ref]
        options += [url, path]

        try:
            int(ref, base=16)
            # ref is probably a commit hash
            if _get_git_version() >= Version('2.49.0'):
                # Use the revision option
                options[options.index('--branch')] = '--revision'
                subprocess.run(options, check=True)
            else:
                # Use a full clone as a last resort
                clone = 'git clone --recursive' if recursive else 'git clone'
                command = [f'{clone} -c advice.detachedHead=false {url} {path} && cd {path} && git reset --hard {ref}']
                subprocess.run(command, check=True, shell=True)
        except (TypeError, ValueError):
            subprocess.run(options, check=True)


def get_commit(path: str) -> str:
    stdout = subprocess.run([f'git -C {path} rev-parse HEAD'], stdout=subprocess.PIPE, shell=True, check=True).stdout

    return stdout.decode('utf-8').strip()

def get_tag(path: str) -> str:
    command = [f'cd {path} && git fetch && git tag --points-at HEAD']
    result = subprocess.run(command, stdout=subprocess.PIPE, shell=True, check=True)

    return result.stdout.decode('utf-8').strip()

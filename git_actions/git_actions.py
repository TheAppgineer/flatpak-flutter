import subprocess


def fetch_repos(repos: list):
    def by_path_depth(fetch_repo):
        return len(str(fetch_repo[2]).split('/'))

    repos.sort(key=by_path_depth)

    for url, ref, path, shallow, recursive in repos:
        options = ['git', 'clone']
        if shallow and recursive:
            options += ['--shallow-submodules']
        if shallow:
            options += ['--depth', '1']
        if recursive:
            options += ['--recurse-submodules']
        if ref:
            options += ['--branch', ref]
        options += [url, path]

        return_code = subprocess.run(options).returncode

        if return_code != 0 and ref:
            # ref is probably a commit hash
            # Try the revision option first (requires git >= 2.49.0)
            options[options.index('--branch')] = '--revision'
            return_code = subprocess.run(options).returncode

            if return_code != 0:
                # Use a full clone as a last resort
                clone = 'git clone --recursive' if recursive else 'git clone'
                command = [f'{clone} {url} {path} && cd {path} && git reset --hard {ref}']
                return_code = subprocess.run(command, shell=True).returncode

        if return_code != 0:
            return return_code

    return 0


def get_commit(path: str) -> str:
    stdout = subprocess.run([f'git -C {path} rev-parse HEAD'], stdout=subprocess.PIPE, shell=True, check=True).stdout

    return stdout.decode('utf-8').strip()

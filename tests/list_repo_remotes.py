import os
from pathlib import Path

import git.exc
from git import Repo

basepath = "~/code/"  # os.getcwd()
dirs = sorted(Path(os.path.expanduser(basepath)).glob("*"))

repo_remotes = {}

print("\n")
for d in dirs:
    if not d.is_dir():
        continue

    try:
        repo = Repo(d.as_posix())
    except git.exc.InvalidGitRepositoryError:
        # print("-- not a repo --")
        continue

    print(d.name)
    rurl = []
    for remote in Repo(d.as_posix()).remotes:
        print(remote, " : ", remote.url)
        rurl.append(remote.url)
    print("\n")

    repo_remotes[d.name] = rurl

print(repo_remotes)

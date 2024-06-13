#   Copyright 2024 hidenorly
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import os
import subprocess
import re
from datetime import datetime
from pathlib import Path
import argparse

def get_tail_commit(repo_path):
    result = subprocess.run(['git', 'rev-list', '--no-merges', '--max-parents=0', 'HEAD'], cwd=repo_path, check=True, stdout=subprocess.PIPE, universal_newlines=True)
    return result.stdout.strip()

def generate_patches(repo_path, output_dir, tail_commit, git_options=[]):
    os.makedirs(output_dir, exist_ok=True)
    cmd_ops = ['git', 'format-patch', f'{tail_commit}..HEAD', '--output-directory', output_dir]
    if git_options:
        cmd_ops.extend(git_options)
    subprocess.run(cmd_ops, cwd=repo_path, check=True, capture_output=True, text=True)

def generate_patches_all(repo_path, patches_dir, git_options=[]):
    tail = get_tail_commit(repo_path)
    generate_patches(repo_path, patches_dir, tail, git_options)
    return patches_dir


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert git to .patch')
    parser.add_argument('-g', '--git', required=True, help='Path to the git directory')
    parser.add_argument('-o', '--gitopt', default="--no-merges", help='git option')
    parser.add_argument('-p', '--patch', required=True, help='Path to the output directory')
    parser.add_argument('-v', '--verbose', default=False, action='store_true', help='verbose output')

    args = parser.parse_args()

    generate_patches_all(args.git, args.patch, args.gitopt.split(" "))

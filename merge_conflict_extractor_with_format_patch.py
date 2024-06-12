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

def get_patch_date(patch_file):
    with open(patch_file, 'r') as f:
        for line in f:
            if line.startswith('Date: '):
                date_str = line.split('Date: ')[1].strip()
                return datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %z')

def get_commit_id(patch_path):
    result = None
    with open(patch_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('From '):
                result=line.split()[1].strip()
                break
    return result

def apply_patch(patch_path, repo_path):
    result = None
    try:
#        result = subprocess.run(['git', 'am', '-3', patch_path], cwd=repo_path, capture_output=True, text=True, timeout=10)
        result = subprocess.run(['git', 'am', patch_path], cwd=repo_path, capture_output=True, text=True, timeout=10)
    except subprocess.TimeoutExpired:
        print("timeout. git am -3 {patch_path}")
        abort_patch(repo_path)
    if not result or (result and result.returncode):
        try:
#            result = subprocess.run(['git', 'apply', '--3way', patch_path], cwd=repo_path, capture_output=True, text=True, timeout=10)
            result = subprocess.run(['git', 'apply', patch_path], cwd=repo_path, capture_output=True, text=True, timeout=10)
        except subprocess.TimeoutExpired:
            print("timeout. git apply --3way {patch_path}")
            abort_patch(repo_path)
    return result

def abort_patch(repo_path):
    subprocess.run(['git', 'am', '--abort'], cwd=repo_path, capture_output=True, text=True)
    subprocess.run(['git', 'reset', '--hard'], cwd=repo_path, capture_output=True, text=True)

def get_conflict_files(result):
    conflicted_files = []
    if result:
        for line in result.stdout.split("\n"):
            line = line.strip()
            if line.startswith("CONFLICT (content): Merge conflict in "):
                pos = line.rfind(" ")
                if pos!=None:
                    filename = line[pos+1:]
                    if filename:
                        conflicted_files.append(filename)
    return conflicted_files

def get_start_end_position_with_margin_without_another_merge_conflict_section(content, conflict_start, conflict_end, margin_lines):
    conflict_start = max(0, conflict_start-margin_lines)
    conflict_end = min(len(content), conflict_end+margin_lines+1)
    # TODO: check whethe the margin area includes another conflict section or not and exclude it.
    return conflict_start, conflict_end

def get_conflict_sections(conflict_file, repo_path, margin_lines):
    results = []
    with open(os.path.join(repo_path, conflict_file), 'r', encoding='utf-8') as cf:
        content = cf.readlines()
        conflict_start = None
        for i, line in enumerate(content):
            if line.startswith('<<<<<<<'):
                conflict_start = i
            elif conflict_start and line.startswith('>>>>>>>'):
                conflict_start, conflict_end = get_start_end_position_with_margin_without_another_merge_conflict_section(content, conflict_start, i, margin_lines)
                results.append(content[conflict_start:conflict_end])
                conflict_start = None
    return results

def get_marker_head_tail(conflict_sections):
    # section is consisted of margin,conflict_section,margin
    # the margins are extracted to header and footer per section
    results = []
    for section in conflict_sections:
        header = None
        footer = None
        for i, line in enumerate(section):
            if line.startswith('<<<<<<<'):
                header = section[:i]
            elif line.startswith('>>>>>>>'):
                footer = section[i+1:]
                break
        results.append( [header, footer] )

def get_match_position(source_lines, target_lines):
    result = 0

    for d, target_line in enumerate(target_lines):
        target_line = target_line.strip()
        for i, line in enumerate(source_lines):
            if line.strip() == target_line:
                result = max(i, result)
                break

    return result

def get_resolved_contents(conflict_file, repo_path, resolved_repo, conflict_sections):
    merge_commit = subprocess.run(['git', 'rev-list', '--merges', '--ancestry-path', '--reverse', f'HEAD...{resolved_repo}'], cwd=repo_path, capture_output=True, text=True)
    merge_commit_hash = merge_commit.stdout.strip().split('\n')[0]
    resolved_content = subprocess.run(['git', 'show', f'{merge_commit_hash}:{conflict_file}'], cwd=repo_path, capture_output=True, text=True)

    content = resolved_content.stdout.splitlines()
    resolved_section = []

    conflict_section_markers = get_marker_head_tail(conflict_sections)
    for conflict_section_marker in conflict_section_markers:
        header = conflict_section_marker[0]
        footer = conflict_section_marker[1]
        start_pos = get_match_position(content, header)
        end_pos = get_match_position(content, footer)
        if start_pos and end_pos:
            start_pos = min(start_pos, len(contents))
            end_pos = max(end_pos-len(footer), start_pos)
            resolved_section.append( content[start_pos+1:end_pos] )
        else:
            resolved_section.append( "NOT FOUND" )

def output_conflict(output_path, conflict_file, conflict_sections, resolved_contents):
    with open(output_path, 'a', encoding='utf-8') as f:
        for conflict_section, resolved_content in zip(conflict_sections, resolved_contents):
            f.write(f"```conflict:{conflict_file}\n")
            f.writelines(conflict_section)
            f.write("```\n")
            f.write(f"```resolution:{conflict_file}\n")
            f.write(resolved_content)
            f.write("\n```\n")

def create_target_repo(target_dir):
    os.makedirs(target_dir, exist_ok=True)
    subprocess.run(['git', 'init'], cwd=target_dir, check=True)

def get_tail_commit(repo_path):
    result = subprocess.run(['git', 'rev-list', '--no-merges', '--max-parents=0', 'HEAD'], cwd=repo_path, check=True, stdout=subprocess.PIPE, universal_newlines=True)
    return result.stdout.strip()

def generate_patches(repo_path, output_dir, tail_commit, git_options=[]):
    os.makedirs(output_dir, exist_ok=True)
    cmd_ops = ['git', 'format-patch', f'{tail_commit}..HEAD', '--no-merges', '--output-directory', output_dir]
    if git_options:
        cmd_ops.extend(git_options)
    subprocess.run(cmd_ops, cwd=repo_path, check=True, capture_output=True, text=True)

def generate_patches_all(repo_path, output_path, prefix, git_options=[]):
    tail = get_tail_commit(repo_path)
    patches_dir = os.path.join(output_path, prefix)
    generate_patches(repo_path, patches_dir, tail, git_options)
    return patches_dir

def get_patch_date(patch_file):
    result = None
    try:
        with open(patch_file, 'r', encoding='utf-8') as f:
            for line in f.readlines():
                if line.startswith('Date: '):
                    date_str = line.split('Date: ')[1].strip()
                    result = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %z')
    except:
        pass
    return result

def main(upstream, downstream, downstream_gitopts, temp_dir, output_dir, margin_lines, verbose):
    # initialize target directory
    target_dir = os.path.join(temp_dir, 'target')
    create_target_repo(target_dir)

    # create .patches
    git_opts = []#["--no-merges"]
    upstream_patches = generate_patches_all(upstream, temp_dir, "upstream", git_opts)
    if downstream_gitopts:
        git_opts.extend(downstream_gitopts.split(" "))
    downstream_patches = generate_patches_all(downstream, temp_dir, "downstream", git_opts)

    patch_files = {}
    for patch_dir in [upstream_patches, downstream_patches]:
        for patch_file in Path(patch_dir).glob('*.patch'):
            patch_date = get_patch_date(patch_file)
            if patch_date:
                patch_files[patch_file] = patch_date
    patch_files = [patch_file for patch_file in sorted(patch_files.keys(), key=patch_files.get)]

    repo_path = target_dir
    resolved_repo = downstream

    for patch_file in patch_files:
        patch_filename = os.path.basename(patch_file)
        commit_id = get_commit_id(patch_file)
        if commit_id:
            print(f'{commit_id} : {patch_file}...')
            result = apply_patch(patch_file, repo_path)
            if verbose and result and result.returncode:
                print(result.stderr)
            conflict_files = get_conflict_files(result)
            if conflict_files:
                print(f'conflicted files:{conflict_files}')

            if conflict_files:
                output_filename = f"{commit_id}-{patch_filename.replace('.patch', '')}.conflict"
                with open(output_filename, 'w', encoding='utf-8') as f:
                    f.close()

                for conflict_file in conflict_files:
                    print(output_filename)
                    output_path = os.path.join(output_dir, output_filename)
                    conflict_sections = get_conflict_sections(conflict_file, repo_path, margin_lines)
                    resolved_contents = get_resolved_contents(conflict_file, repo_path, resolved_repo, conflict_sections)
                    output_conflict(output_path, conflict_file, conflict_sections, resolved_contents)

                    #abort_patch(repo_path)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Apply patches and output merge conflicts')
    parser.add_argument('-u', '--upstream', required=True, help='Path to the upstream Git repository')
    parser.add_argument('-d', '--downstream', required=True, help='Path to the downstream Git repository')
    parser.add_argument('-dg', '--downstream_gitopts', default="", help='git options (optional)')
    parser.add_argument('-t', '--temp', required=True, help='Output path of .patch')
    parser.add_argument('-o', '--output-dir', required=True, help='Path to the output directory')
    parser.add_argument('-m', '--margin-lines', type=int, default=3, help='Number of lines to include before and after the conflict section')
    parser.add_argument('-v', '--verbose', default=False, action='store_true', help='verbose output')

    args = parser.parse_args()

    main(args.upstream, args.downstream, args.downstream_gitopts, args.temp, args.output_dir, args.margin_lines, args.verbose)

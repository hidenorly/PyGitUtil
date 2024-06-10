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

def get_commit_id(patch_path):
    with open(patch_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('From '):
                return line.split()[1]
    raise ValueError(f'Could not find commit ID in {patch_path}')

def apply_patch(patch_path, repo_path):
    result = subprocess.run(['git', 'am', '-3', patch_path], cwd=repo_path, capture_output=True, text=True)
    return result

def get_conflict_files(result):
    if 'Applying' in result.stdout and 'Conflicts' in result.stdout:
        return re.findall(r'Conflicts:\n\t(.*?)\n', result.stdout)
    return []

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

def abort_patch(repo_path):
    subprocess.run(['git', 'am', '--abort'], cwd=repo_path)

def main(repo_path, patch_dir, output_dir, margin_lines, resolved_repo):
    patch_files = [os.path.join(patch_dir, f) for f in os.listdir(patch_dir) if f.endswith('.patch')]

    for patch_file in patch_files:
        patch_filename = os.path.basename(patch_file)
        try:
            commit_id = get_commit_id(patch_file)
        except ValueError as e:
            print(f'Error: {e}')
            continue
        result = apply_patch(patch_file, repo_path)
        conflict_files = get_conflict_files(result)

        if conflict_files:
            output_filename = f"{commit_id}-{patch_filename.replace('.patch', '')}.conflict"
            with open(output_path, 'w', encoding='utf-8') as f:
                f.close()

            for conflict_file in conflict_files:
                output_path = os.path.join(output_dir, output_filename)
                conflict_sections = get_conflict_sections(conflict_file, repo_path, margin_lines)
                resolved_contents = get_resolved_contents(conflict_file, repo_path, resolved_repo, conflict_sections)
                output_conflict(output_path, conflict_file, conflict_sections, resolved_contents)

            abort_patch(repo_path)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Apply patches and output merge conflicts')
    parser.add_argument('-t', '--repo-path', default='.', help='Path to the Git repository')
    parser.add_argument('-p', '--patch-dir', required=True, help='Path to the directory containing patch files')
    parser.add_argument('-o', '--output-dir', required=True, help='Path to the output directory')
    parser.add_argument('-m', '--margin-lines', type=int, default=3, help='Number of lines to include before and after the conflict section')
    parser.add_argument('-r', '--resolved-repo', required=True, help='Path to the Git repository containing the resolved merge commits')

    args = parser.parse_args()

    main(args.repo_path, args.patch_dir, args.output_dir, args.margin_lines, args.resolved_repo)

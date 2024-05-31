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

import re
import argparse

def read_file(file_path):
    lines = []
    with open(file_path, 'r') as f:
        lines = f.readlines()
    return lines

def get_conflicted_sections(lines):
    conflicted_sections = []

    conflict_start = None
    for i, line in enumerate(lines):
        if line.startswith('<<<<<<< '):
            conflict_start = i
        elif line.startswith('>>>>>>> '):
            if conflict_start!=None:
                conflicted_sections.append([conflict_start, i])
                conflict_start = None

    return conflicted_sections

def check_conflicted_section_with_target_diff(conflicted_section_lines, diff_lines):
    stripped_conflict_section = [re.sub(r'<<<<<<<\s*\w*|=======|>>>>>>> \s*\w*', '', line) for line in conflicted_section_lines]
    stripped_diff_section = [line[1:].strip('\n') if line.startswith('-') else line.strip('\n') for line in diff_lines]

    if any(line in ''.join(stripped_conflict_section) for line in stripped_diff_section):
        return True

    return False

def apply_diff(conflicted_section_lines, diff_lines):
    resolved_lines = []

    for line in diff_lines:
        _line = None
        if line.startswith('+'):
            _line = line[1:].strip('\n')
        else:
            _line = line.strip('\n')
        if _line!=None:
            resolved_lines.append(_line)

    return resolved_lines




def solve_merge_conflict(merge_conflict_file, resolution_diff_file):
    resolved_lines = []

    merge_conflict_lines = read_file(merge_conflict_file)
    resolution_diff_lines = read_file(resolution_diff_file)

    conflicted_sections = get_conflicted_sections(merge_conflict_lines)

    if conflicted_sections:
        length_conflict_lines = len(merge_conflict_lines)

        last_conflicted_section = 0
        for conflict_start, conflict_end in conflicted_sections:
            # last_conflicted_section - conflict_start
            resolved_lines.extend( merge_conflict_lines[last_conflicted_section:conflict_start] )

            last_conflicted_section = conflict_end = min(conflict_end+1, length_conflict_lines)
            conflicted_section_lines = merge_conflict_lines[conflict_start:conflict_end]

            # add resolved conflicted section
            if check_conflicted_section_with_target_diff(conflicted_section_lines, resolution_diff_lines):
                # found target diff section
                resolved_section = apply_diff(conflicted_section_lines, resolution_diff_lines)
                resolved_lines.extend(resolved_section)
            else:
                # this is not target section
                resolved_lines.extend(conflicted_section_lines)

        # add remaining part (last_conflicted_section-end)
        resolved_lines.extend(merge_conflict_lines[last_conflicted_section:])
    else:
        resolved_lines = merge_conflict_lines

    return resolved_lines


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Solve merge conflicts using a resolution diff file.")
    parser.add_argument('-s', '--merge-conflict-file', required=True, help="Path to the merge conflict file")
    parser.add_argument('-d', '--resolution-diff-file', required=True, help="Path to the resolution diff file")
    parser.add_argument('-o', '--output', default=None, help="If not specified, stdout")
    args = parser.parse_args()

    resolved_lines = solve_merge_conflict(args.merge_conflict_file, args.resolution_diff_file)
    if args.output:
        with open(merge_conflict_file, 'w') as f:
            f.writelines(line + '\n' for line in resolved_lines)
    else:
        for line in resolved_lines:
            print(line)







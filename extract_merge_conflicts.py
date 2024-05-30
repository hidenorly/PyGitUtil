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
import argparse
import subprocess

def get_conflict_candidate_files():
    conflict_files = []
    git_status_output = subprocess.check_output(['git', 'status', '--porcelain']).decode('utf-8')
    if git_status_output:
        for line in git_status_output.split('\n'):
            if line.startswith('UU'):
                status_result = line.split(' ')
                if len(status_result)>=2:
                    conflict_files.append(status_result[1])
    return conflict_files

def extract_conflict_line_position_sections(lines):
    conflict_sections = []

    if lines:
        start_line = None
        start_marker = '<<<<<<<'
        end_marker = '>>>>>>>'
        for i, line in enumerate(lines):
            if start_marker in line:
                start_line = i
            elif end_marker in line:
                if start_line!=None:
                    conflict_sections.append( [start_line, i] )
                start_line = None

    return conflict_sections

def read_file(file_path):
    lines = []
    if file_path and os.path.exists(file_path):
        with open(file_path, 'r') as file:
            lines = file.readlines()
    return lines

def extract_conflict_sections(file_path, margin_line_count):
    lines = read_file(file_path)
    conflict_sections = extract_conflict_line_position_sections(lines)
    extracted_sections = []
    for section in conflict_sections:
        start = max(section[0]-margin_line_count, 0)
        end = min(section[1]+margin_line_count+1, len(lines))
        extracted_sections.append(lines[start:end])
    return extracted_sections

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-m', '--margin', type=int, default=3, help='margin line count')
    args = parser.parse_args()

    conflict_files = get_conflict_candidate_files()

    for file_path in conflict_files:
        print(f'Conflicted file: {file_path}')
        extracted_sections = extract_conflict_sections(file_path, margin_line_count=args.margin)
        for conflicted_lines in extracted_sections:
            for line in conflicted_lines:
                print(line.rstrip())
        print('---')

if __name__ == '__main__':
    main()

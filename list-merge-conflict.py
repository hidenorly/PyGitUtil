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

import subprocess

# Run a git command and return the output
def run_git_command(command, cwd=None, combineStdErr=False):
    result = subprocess.run(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    error_result = ""
    if result.returncode != 0:
        error_result = result.stderr.strip()
        raise Exception(f"Git command failed: {' '.join(command)}\n{error_result}")
    result = result.stdout.strip()
    if combineStdErr:
        result += error_result
    return result

# Get a list of merge commits
def get_merge_commits():
    command = ["git", "log", "--merges", "--pretty=format:%H"]
    return run_git_command(command).splitlines()

# Get the parent commits of a given commit
def get_commit_parents(commit):
    command = ["git", "show", "--pretty=format:%P", "-s", commit]
    parents = run_git_command(command).split()
    if len(parents) < 2:
        raise Exception(f"Commit {commit} is not a merge commit.")
    return parents

# Get the current HEAD commit
def get_current_head():
    return run_git_command(["git", "rev-parse", "HEAD"])

# Get the current branch name
def get_current_branch():
    return run_git_command(["git", "rev-parse", "--abbrev-ref", "HEAD"])

# Stash local changes
def stash_changes():
    run_git_command(["git", "stash", "push", "-m", "temporary stash"])

# Pop the last stash entry
def pop_stash():
    run_git_command(["git", "stash", "pop"])

# Checkout a specific branch
def checkout_branch(branch):
    run_git_command(["git", "checkout", branch])

# Checkout a specific commit
def checkout_commit(commit):
    run_git_command(["git", "checkout", commit])

# Reset the current branch to a specific commit
def reset_hard(commit):
    run_git_command(["git", "reset", "--hard", commit])

# Create a temporary branch and checkout to it
def create_temp_branch():
    temp_branch = "temp-branch"
    run_git_command(["git", "checkout", "-b", temp_branch])
    return temp_branch

# Delete a specific branch
def delete_branch(branch):
    run_git_command(["git", "branch", "-D", branch])

# Perform a merge without committing
def merge_no_commit(commit):
    return run_git_command(["git", "merge", commit, "--no-commit", "--no-ff"], combineStdErr=True)

# Abort the current merge
def abort_merge():
    run_git_command(["git", "merge", "--abort"])

# Get the list of files with merge conflicts
def get_conflict_files():
    status_output = run_git_command(["git", "status", "--porcelain"])
    conflict_files = [line[3:] for line in status_output.splitlines() if line.startswith("UU ")]
    return conflict_files

# Get the content of a file
def get_file_content(file_path):
    with open(file_path, "r") as file:
        return file.read()

def main():
    try:
        current_head = get_current_head()
        current_branch = get_current_branch()
        merge_commits = get_merge_commits()
        
        stash_needed = False

        # Stash local changes if any
        try:
            if run_git_command(["git", "status", "--porcelain"]):
                stash_needed = True
                stash_changes()

            for merge_commit in merge_commits:
                parents = get_commit_parents(merge_commit)
                parent1_commit_id, parent2_commit_id = parents[0], parents[1]

                # Create a temporary branch and reset it to the first parent commit
                temp_branch = create_temp_branch()
                reset_hard(parent1_commit_id)

                try:
                    # Perform the merge without committing
                    result = merge_no_commit(parent2_commit_id)
                    if result:
                        print(f'{merge_commit}:{parent1_commit_id}...{parent2_commit_id}:{result}')

                    # Get the list of conflict files
                    conflict_files = get_conflict_files()

                    if conflict_files:
                        print(f"\nMerge commit: {merge_commit}")
                        for conflict_file in conflict_files:
                            print(f"\nConflict file: {conflict_file}")
                            content = get_file_content(conflict_file)
                            print(content)

                except Exception as e:
                    print(f"Error during merge: {e}")
                finally:
                    # Abort the merge if there was a conflict
                    try:
                        abort_merge()
                    except Exception:
                        pass
                    # Return to the original commit before deleting the temp branch
                    checkout_commit(current_head)
                    delete_branch(temp_branch)

        finally:
            # Pop the stash if it was needed
            if stash_needed:
                pop_stash()
            # Checkout back to the original branch
            checkout_branch(current_branch)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()

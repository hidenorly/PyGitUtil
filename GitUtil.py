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

class GitUtil:
    # Run a git command and return the output
    @staticmethod
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
    @staticmethod
    def get_merge_commits():
        command = ["git", "log", "--merges", "--pretty=format:%H"]
        return GitUtil.run_git_command(command).splitlines()

    # Get the parent commits of a given commit
    @staticmethod
    def get_commit_parents(commit):
        command = ["git", "show", "--pretty=format:%P", "-s", commit]
        parents = GitUtil.run_git_command(command).split()
        if len(parents) < 2:
            raise Exception(f"Commit {commit} is not a merge commit.")
        return parents

    # Get the current HEAD commit
    @staticmethod
    def get_current_head():
        return GitUtil.run_git_command(["git", "rev-parse", "HEAD"])

    # Get the current branch name
    @staticmethod
    def get_current_branch():
        return GitUtil.run_git_command(["git", "rev-parse", "--abbrev-ref", "HEAD"])

    # Stash local changes
    @staticmethod
    def stash_changes():
        GitUtil.run_git_command(["git", "stash", "push", "-m", "temporary stash"])

    # Pop the last stash entry
    @staticmethod
    def pop_stash():
        GitUtil.run_git_command(["git", "stash", "pop"])

    # Checkout a specific branch
    @staticmethod
    def checkout_branch(branch):
        GitUtil.run_git_command(["git", "checkout", branch])

    # Checkout a specific commit
    @staticmethod
    def checkout_commit(commit):
        GitUtil.run_git_command(["git", "checkout", commit])

    # Reset the current branch to a specific commit
    @staticmethod
    def reset_hard(commit):
        GitUtil.run_git_command(["git", "reset", "--hard", commit])

    # Create a temporary branch and checkout to it
    @staticmethod
    def create_temp_branch():
        temp_branch = "temp-branch"
        GitUtil.run_git_command(["git", "checkout", "-b", temp_branch])
        return temp_branch

    # Delete a specific branch
    @staticmethod
    def delete_branch(branch):
        GitUtil.run_git_command(["git", "branch", "-D", branch])

    # Perform a merge without committing
    @staticmethod
    def merge_no_commit(commit):
        return GitUtil.run_git_command(["git", "merge", commit, "--no-commit", "--no-ff"], combineStdErr=True)

    # Abort the current merge
    @staticmethod
    def abort_merge():
        GitUtil.run_git_command(["git", "merge", "--abort"])

    # git status
    @staticmethod
    def get_status():
        return GitUtil.run_git_command(["git", "status", "--porcelain"])

    # Get the list of files with merge conflicts
    @staticmethod
    def get_conflict_files():
        status_output = GitUtil.get_status()
        conflict_files = [line[3:] for line in status_output.splitlines() if line.startswith("UU ")]
        return conflict_files

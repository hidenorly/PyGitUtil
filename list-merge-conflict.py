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

from GitUtil import GitUtil


# Get the content of a file
def get_file_content(file_path):
    with open(file_path, "r") as file:
        return file.read()

def main():
    try:
        current_head = GitUtil.get_current_head()
        current_branch = GitUtil.get_current_branch()
        merge_commits = GitUtil.get_merge_commits()
        
        stash_needed = False

        # Stash local changes if any
        try:
            if GitUtil.get_status():
                stash_needed = True
                GitUtil.stash_changes()

            for merge_commit in merge_commits:
                parents = GitUtil.get_commit_parents(merge_commit)
                parent1_commit_id, parent2_commit_id = parents[0], parents[1]

                # Create a temporary branch and reset it to the first parent commit
                temp_branch = GitUtil.create_temp_branch()
                GitUtil.reset_hard(parent1_commit_id)

                try:
                    # Perform the merge without committing
                    result = GitUtil.merge_no_commit(parent2_commit_id)
                    if result:
                        print(f'{merge_commit}:{parent1_commit_id}...{parent2_commit_id}:{result}')

                    # Get the list of conflict files
                    conflict_files = GitUtil.get_conflict_files()

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
                        GitUtil.abort_merge()
                    except Exception:
                        pass
                    # Return to the original commit before deleting the temp branch
                    GitUtil.checkout_commit(current_head)
                    GitUtil.delete_branch(temp_branch)

        finally:
            # Pop the stash if it was needed
            if stash_needed:
                GitUtil.pop_stash()
            # Checkout back to the original branch
            GitUtil.checkout_branch(current_branch)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()

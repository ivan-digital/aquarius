# repo_scanner.py

import os

class RepoScanner:
    def __init__(self, exts_to_index=(".py", ".java", ".cpp", ".c")):
        self.exts_to_index = exts_to_index

    def scan_repo(self, local_repo_path):
        """
        Return a list of source files to index from the given local repo path.
        """
        source_files = []
        for root, dirs, files in os.walk(local_repo_path):
            for fname in files:
                if fname.endswith(self.exts_to_index):
                    source_files.append(os.path.join(root, fname))
        return source_files
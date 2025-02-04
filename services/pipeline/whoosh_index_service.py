# whoosh_index_service.py

import os
from whoosh.fields import Schema, TEXT, ID
from whoosh.analysis import StemmingAnalyzer
from whoosh.filedb.filestore import FileStorage
from whoosh.qparser import QueryParser

INDEX_DIR = "index_storage"

class WhooshIndexService:
    def __init__(self, index_dir=INDEX_DIR):
        self.index_dir = index_dir
        self.schema = Schema(
            path=ID(stored=True),
            class_name=ID(stored=True),
            description=TEXT(analyzer=StemmingAnalyzer(), stored=True),
            file_extension=ID(stored=True),
        )
        self._ensure_index_exists()

    def _ensure_index_exists(self):
        """
        Ensure a Whoosh index exists at self.index_dir.
        If it doesn't, create it.
        """
        if not os.path.exists(self.index_dir):
            os.makedirs(self.index_dir)

        storage = FileStorage(self.index_dir)
        if not storage.index_exists("MAIN"):
            storage.create_index(self.schema)

    def create_whoosh_index_in_chunks(self, entries, chunk_size=5):
        """
        Create/Update a Whoosh index in chunks (partial commits).
        Yields log messages after each commit so the caller can show intermediate progress.
        :param entries: List of dicts with keys: "path", "class_name", "description", "file_extension"
        :param chunk_size: Number of documents to add before forcing a commit.
        :yield: Log messages describing the progress.
        """
        storage = FileStorage(self.index_dir)
        idx = storage.open_index()
        writer = idx.writer()
        indexed_count = 0
        total_entries = len(entries)

        for e in entries:
            writer.add_document(
                path=e["path"],
                class_name=e["class_name"],
                description=e["description"],
                file_extension=e["file_extension"]
            )
            indexed_count += 1

            if indexed_count % chunk_size == 0:
                writer.commit()
                yield f"Committed {indexed_count} entries so far."
                writer = idx.writer()

        writer.commit()
        yield f"Final commit: {indexed_count} entries indexed out of {total_entries}."

    def list_indexed_classes_for_repo(self, repo_name):
        """
        Search the Whoosh index for all documents whose 'path' contains the repo name.
        Returns a list of dicts with keys: path, class_name, description, file_extension.
        """
        storage = FileStorage(self.index_dir)
        if not storage.index_exists("MAIN"):
            return []

        idx = storage.open_index()
        with idx.searcher() as searcher:
            parser = QueryParser("path", idx.schema)
            query = parser.parse(f"cloned_repos/{repo_name}*")
            results = searcher.search(query, limit=None)

            data = []
            for r in results:
                data.append({
                    "path": r["path"],
                    "class_name": r["class_name"],
                    "description": r["description"],
                    "file_extension": r["file_extension"]
                })
        return data
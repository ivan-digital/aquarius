import gradio as gr
from whoosh.qparser import QueryParser
from whoosh.filedb.filestore import FileStorage
from whoosh.query import Every

INDEX_DIR = "index_storage"

def list_indexed_classes_for_repo(repo_name):
    """
    Search the Whoosh index for all documents whose 'path' contains the repo name.
    Returns a list of dict with keys: path, class_name, description, file_extension
    """
    storage = FileStorage(INDEX_DIR)
    if not storage.index_exists("MAIN"):
        return []

    idx = storage.open_index()
    with idx.searcher() as searcher:
        parser = QueryParser("path", idx.schema)
        # Adjust this pattern to match how your repo files are stored (e.g. "cloned_repos/<repo_name>")
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

def create_index_explorer_tab(local_repo_dropdown):
    """Creates the Index Explorer tab UI."""
    with gr.Tab("Index Explorer"):
        gr.Markdown("## Explore Indexed Classes")
        gr.Markdown("### 1) Select Repo (Dropdown in 'Chat' tab)")

        # Button to list indexed classes
        list_indexed_btn = gr.Button("List Indexed Classes")

        # Dataframe to display results
        index_table = gr.Dataframe(
            headers=["Path", "Class Name", "Description"],
            row_count=0,
            col_count=3,
            wrap=True
        )

        # Define the callback for button
        def on_list_indexed_classes(selected_local_repo):
            if not selected_local_repo:
                return [["No repo selected", "", ""]]

            data = list_indexed_classes_for_repo(selected_local_repo)
            if not data:
                return [["No entries found in index for repo", "", ""]]

            # Return row entries for the Gradio Dataframe
            table_data = []
            for d in data:
                # Keep only path, class_name, and description for display
                table_data.append([d["path"], d["class_name"], d["description"]])

            return table_data

        list_indexed_btn.click(
            fn=on_list_indexed_classes,
            inputs=[local_repo_dropdown],
            outputs=[index_table]
        )

    return index_table

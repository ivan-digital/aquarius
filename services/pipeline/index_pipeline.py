import os
import datetime
import time
import gradio as gr

from services.pipeline.whoosh_index_service import WhooshIndexService
from services.pipeline.class_extractor import ClassExtractor
from services.pipeline.repo_scanner import RepoScanner


class IndexPipeline:
    def __init__(self, llm_client):
        self.llm_client = llm_client
        self.index_service = WhooshIndexService()
        self.class_extractor = ClassExtractor()
        self.repo_scanner = RepoScanner()

    def index_repo_generator(self, selected_local_repo: str, progress=gr.Progress()):
        """
        A generator function that updates a custom Gradio Progress bar
        while indexing the selected repo. We have removed the
        build-related steps so this is purely for indexing now.
        """
        logs = []

        def log(msg: str):
            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            line = f"[{ts}] {msg}"
            print(line)
            # Instead of accumulating all logs, you can yield incrementally
            # or store them in 'logs'. Below we just do single-line returns.
            return msg

        # 1) Validate input
        progress(0.0, desc="Starting indexing pipeline")
        if not selected_local_repo:
            yield log("No local repo selected. Please pick one first.")
            return

        local_path = os.path.join("cloned_repos", selected_local_repo)
        if not os.path.exists(local_path):
            yield log(f"Repo not found locally: {selected_local_repo}")
            return

        # 2) Gather & check previously processed
        existing_entries = self.index_service.list_indexed_classes_for_repo(selected_local_repo)
        processed_files = {e["path"] for e in existing_entries if len(e["description"]) > 30}
        source_files = self.repo_scanner.scan_repo(local_path)
        unprocessed_files = [f for f in source_files if f not in processed_files]

        total_files_to_do = len(unprocessed_files)
        # We'll do 1 step for each unprocessed file + a few overhead steps
        total_steps = 3 + total_files_to_do
        current_step = 0

        def update_progress(desc):
            nonlocal current_step
            current_step += 1
            fraction = current_step / total_steps
            progress(fraction, desc=desc)

        # Step A: Checking processed
        update_progress("Checking processed files...")
        yield log(f"Already processed {len(processed_files)} file(s).")

        # Step B: Gathering source files
        update_progress("Gathering source files...")
        yield log(f"Found {len(source_files)} total source files.")

        if not source_files:
            yield log("No source files found. Aborting.")
            return

        # Step C: Iterate over unprocessed files for LLM annotation
        all_annotations = []
        class_entries = []

        update_progress("Analyzing unprocessed files with LLM...")
        for idx, fpath in enumerate(source_files, start=1):
            if fpath in processed_files:
                # skip
                continue

            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as ff:
                    content = ff.read()

                prompt = (
                    "Prepare a functional summary of the code below. "
                    "This summary will help with code navigation:\n\n"
                    f"{content}\n"
                )
                annotation = self.llm_client.generate_single(prompt)
                all_annotations.append((fpath, annotation))

                cdescs = self.class_extractor.extract_classes_and_descriptions(
                    fpath, content, annotation["response"]
                )
                class_entries.extend(cdescs)

                time.sleep(0.1)
                update_progress(f"Indexing file: {os.path.basename(fpath)}")
                yield log(f"[{idx}/{len(source_files)}] Indexed: {os.path.basename(fpath)}")

            except Exception as e:
                update_progress(f"Error reading file: {os.path.basename(fpath)}")
                yield log(f"Error reading {fpath}: {str(e)}")

        # (Removed the build analysis and execution steps entirely)

        # Final step: Create Whoosh index
        update_progress("Creating Whoosh index...")
        yield log(f"Creating Whoosh index with {len(class_entries)} entries...")

        for commit_msg in self.index_service.create_whoosh_index_in_chunks(class_entries, chunk_size=5):
            yield log(commit_msg)

        yield log("Indexing complete!")
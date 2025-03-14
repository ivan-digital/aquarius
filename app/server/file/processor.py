import os
import json
import zipfile
from werkzeug.utils import secure_filename


class ZipFileProcessor:
    """
    Processes an uploaded ZIP file by extracting its contents and optionally annotating code files
    using an LLM processor. Now accepts a file path (the ZIP has already been saved).
    """

    def __init__(self, upload_folder, extract_folder, llm_processor=None, log_service=None):
        """
        :param upload_folder: Directory to store uploaded ZIP files.
        :param extract_folder: Directory where the ZIP file will be extracted.
        :param llm_processor: Optional LLMFileAnnotator instance for code annotation.
        :param log_service: Service for logging messages.
        """
        self.upload_folder = upload_folder
        self.extract_folder = extract_folder
        self.llm_processor = llm_processor
        self.log_service = log_service
        os.makedirs(self.upload_folder, exist_ok=True)
        os.makedirs(self.extract_folder, exist_ok=True)

    def process_zip(self, zip_path):
        """
        Process the ZIP file at the given file path: extract its contents and, if configured, annotate
        supported code files. Returns an HTTP-like status code.

        :param zip_path: The path to the saved ZIP file.
        :return: status code (200 for success, 400/500 for errors)
        """
        self.log_service.add_log("Starting processing...")

        if not zip_path or not os.path.exists(zip_path):
            self.log_service.add_log("File does not exist.")
            return 400

        safe_name = secure_filename(os.path.basename(zip_path))
        self.log_service.add_log(f"Processing ZIP file: {safe_name}")

        # Create a dedicated extraction folder based on the ZIP file name.
        subfolder_name = os.path.splitext(safe_name)[0]
        extraction_path = os.path.join(self.extract_folder, subfolder_name)
        os.makedirs(extraction_path, exist_ok=True)
        self.log_service.add_log(f"Extraction folder created: {extraction_path}")

        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Filter out unwanted entries.
                valid_members = [
                    member for member in zip_ref.infolist()
                    if not (member.filename.startswith('__MACOSX/') or member.filename.endswith('.DS_Store'))
                ]
                total_members = len(valid_members)
                self.log_service.add_log(f"Found {total_members} valid file(s) to extract.")
                for i, member in enumerate(valid_members, 1):
                    zip_ref.extract(member, extraction_path)
                    self.log_service.add_log(f"Extracted {member.filename} ({i}/{total_members})")
            self.log_service.add_log(f"Archive extracted to: {extraction_path}")

            # Gather lists of extracted folders and files.
            extracted_folders = []
            extracted_files = []
            for root, dirs, files in os.walk(extraction_path):
                for d in dirs:
                    extracted_folders.append(os.path.join(root, d))
                for f in files:
                    extracted_files.append(os.path.join(root, f))

            if extracted_folders:
                self.log_service.add_log("Extracted folders:")
                for folder in extracted_folders:
                    self.log_service.add_log(folder)
            else:
                self.log_service.add_log("No folders were extracted.")

            if extracted_files:
                self.log_service.add_log("Extracted files:")
                for file_path in extracted_files:
                    self.log_service.add_log(file_path)
            else:
                self.log_service.add_log("No files were extracted.")

            # If an LLM processor is provided, annotate supported code files.
            supported_extensions = {".py", ".sh", ".txt", ".cpp", ".hpp", ".h", ".java", ".scala", ".kt"}
            if self.llm_processor:
                self.log_service.add_log("Starting LLM file annotation...")
                supported_files = [
                    file_path for file_path in extracted_files
                    if os.path.splitext(file_path)[1] in supported_extensions
                ]
                total_files = len(supported_files)
                self.log_service.add_log(f"{total_files} supported file(s) found for annotation.")
                for index, file_path in enumerate(supported_files, 1):
                    annotation_file = file_path + ".annotation.json"
                    if os.path.exists(annotation_file):
                        self.log_service.add_log(
                            f"Annotation file already present for {file_path}. Skipping annotation.")
                        continue
                    annotation = self.llm_processor.process_files(file_path)
                    with open(annotation_file, "w", encoding="utf-8") as f:
                        json.dump(annotation, f, indent=2)
                    self.log_service.add_log(
                        f"Annotated file {file_path} ({index}/{total_files}) – annotation written to: {annotation_file}"
                    )
                    self.log_service.add_log(
                        f"Annotation {annotation}"
                    )
                self.log_service.add_log("LLM file annotation complete.")

            self.log_service.add_log("Processing complete.")
            return 200

        except zipfile.BadZipFile:
            self.log_service.add_log("Error: Invalid ZIP file.")
            return 400
        except Exception as e:
            self.log_service.add_log(f"An error occurred: {e}")
            return 500
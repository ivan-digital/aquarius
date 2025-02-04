# class_extractor.py

import os
import re

class ClassExtractor:
    def __init__(self):
        # You might want to parameterize any config, e.g., patterns
        self.class_pattern = r"(?:public\s+|private\s+|protected\s+)?class\s+([A-Za-z0-9_]+)"

    def extract_classes_and_descriptions(self, file_path, file_content, llm_response):
        """
        Given a source file and LLM annotations, produce an array of class descriptions:
          - path
          - class_name
          - description
          - file_extension
        """
        file_extension = os.path.splitext(file_path)[-1]
        class_descriptions = []

        matches = re.findall(self.class_pattern, file_content)

        if matches:
            for cls in matches:
                class_descriptions.append({
                    "path": file_path,
                    "class_name": cls,
                    "description": f"From LLM: {llm_response.strip()}",
                    "file_extension": file_extension
                })
        else:
            # If no classes found, store a single doc with <no_class_found>.
            class_descriptions.append({
                "path": file_path,
                "class_name": "<no_class_found>",
                "description": f"From LLM: {llm_response.strip()}",
                "file_extension": file_extension
            })
        return class_descriptions
import os
import subprocess
from services.llm_client import LlmClient

class BuildService:
    """
    Service to analyze build files and execute builds for a given repository.
    """

    def __init__(self, llm_client: LlmClient = None):
        self.llm_client = llm_client or LlmClient()

    def analyze_build_files(self, local_path: str, combined_annotations: str) -> str:
        """
        Looks for recognized build files (pom.xml, build.gradle, Makefile),
        calls the LLM to interpret them, and returns a text summary
        of how to build/test.
        """
        print("Build analysis started...")
        build_file_paths = {
            "maven": os.path.join(local_path, "pom.xml"),
            "gradle": os.path.join(local_path, "build.gradle"),
            "make": os.path.join(local_path, "Makefile"),
        }

        build_analysis = []
        for system_name, path in build_file_paths.items():
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as bf:
                        content = bf.read()
                    prompt = (
                        f"Analyze this {system_name} build file. Describe the dependencies, "
                        f"build steps, and test steps:\n\n{content}\n"
                    )
                    result = self.llm_client.generate_single(prompt)
                    print(result)
                    build_analysis.append(f"\n**{system_name.upper()} FILE**:\n{result}\n")
                except Exception as e:
                    build_analysis.append(f"Error reading {path}: {str(e)}")
        if build_analysis:
            combined_text = "\n".join(build_analysis) + "\n\n" + combined_annotations
            final_prompt = (
                "Based on the above build files and the file annotations, summarize:\n"
                " - The main language\n - The build system\n - Test framework\n - Build/test steps\n\n"
                f"{combined_text}\n\n"
                "Reply with recommended build/test steps."
            )
            build_instructions = self.llm_client.generate_single(final_prompt)
            return build_instructions
        else:
            return "No recognized build files found or analyzed."

    def execute_build(self, local_path: str) -> str:
        """
        Attempts to execute the build for the project located at local_path.
        Checks for Maven, Gradle, or Makefile.
        Returns build status as a string.
        """
        build_status = "Build not attempted."
        if os.path.exists(os.path.join(local_path, "pom.xml")):
            try:
                subprocess.run(["mvn", "clean", "install"], cwd=local_path, check=True)
                build_status = "Maven build succeeded."
            except subprocess.CalledProcessError as e:
                build_status = f"Maven build failed: {str(e)}"
        elif os.path.exists(os.path.join(local_path, "build.gradle")):
            try:
                subprocess.run(["gradle", "build"], cwd=local_path, check=True)
                build_status = "Gradle build succeeded."
            except subprocess.CalledProcessError as e:
                build_status = f"Gradle build failed: {str(e)}"
        elif os.path.exists(os.path.join(local_path, "Makefile")):
            try:
                subprocess.run(["make"], cwd=local_path, check=True)
                build_status = "Make build succeeded."
            except subprocess.CalledProcessError as e:
                build_status = f"Make build failed: {str(e)}"
        return build_status
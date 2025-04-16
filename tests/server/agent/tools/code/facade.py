from app.agent.tools.code import PythonCodeExecutor


class CodeExecutionFacade:
    def __init__(self, config):
        """
        Initializes the CodeExecutionFacade using the provided configuration.

        Parameters:
            config (dict): Configuration parameters (if needed).
        """
        self.config = config
        self.executor = PythonCodeExecutor()

    def execute(self, code):
        """
        Executes the given Python code snippet and returns the formatted results.

        Parameters:
            code (str): The Python code to execute.

        Returns:
            str: Markdown formatted execution results.
        """
        return self.executor.execute_formatted(code)

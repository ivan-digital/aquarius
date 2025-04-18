import io
import sys
import ast
import traceback


class PythonCodeExecutor:

    def lint_code(self, code):
        """
        Performs a linting check on the provided Python code using the AST module.

        Parameters:
            code (str): The Python code to be linted.

        Returns:
            None if the code is syntactically correct, otherwise returns the syntax error message.
        """
        try:
            ast.parse(code)
        except SyntaxError as e:
            return f"Syntax Error: {e.msg} (line {e.lineno}, offset {e.offset})"
        return None

    def execute(self, code):
        """
        Executes a Python code snippet in a clean environment after lint verification.

        Parameters:
            code (str): The Python code to execute.

        Returns:
            str: The captured output from executing the code or error traceback if an exception occurred.
        """
        lint_error = self.lint_code(code)
        if lint_error:
            return lint_error

        old_stdout = sys.stdout
        redirected_output = io.StringIO()
        sys.stdout = redirected_output
        try:
            # Execute code in an isolated namespace (empty dict)
            exec(code, {})
            output = redirected_output.getvalue()
        except Exception:
            output = "Error executing code:\n" + traceback.format_exc()
        finally:
            sys.stdout = old_stdout
        return output

    def format_results(self, code, execution_result):
        """
        Formats the execution results into a markdown string.

        Parameters:
            code (str): The Python code snippet that was executed.
            execution_result (str): The output or error message from execution.

        Returns:
            str: A markdown formatted string containing the code and its output.
        """
        md = f"# Python Code Execution Results\n\n"
        md += f"### Code Snippet\n\n```python\n{code}\n```\n\n"
        md += f"### Execution Output\n\n```\n{execution_result}\n```\n"
        return md


pythonExecutor = PythonCodeExecutor()


def executePython(code):
    """
    Executes the given Python code snippet and returns a formatted markdown string.
    """
    execution_result = pythonExecutor.execute(code)
    return pythonExecutor.format_results(code, execution_result)

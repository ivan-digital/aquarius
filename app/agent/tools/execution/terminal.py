import subprocess
import shlex
from typing import List, Tuple

# Define allowed and denied commands for security.
# These lists should be populated based on specific security requirements.
# For example, allow common informational commands but deny destructive ones.
COMMAND_ALLOW_LIST: List[str] = [
    "ls",
    "pwd",
    "git status", # Example: allow specific git commands
    "echo"
]
COMMAND_DENY_LIST: List[str] = [
    "rm",
    "sudo",
    # "git push", # Example: deny potentially risky git commands
]

def is_command_allowed(command: str) -> bool:
    """
    Checks if the given command is allowed based on the allow and deny lists.
    A command is allowed if it (or its prefix) is in COMMAND_ALLOW_LIST and
    not in COMMAND_DENY_LIST.
    More specific deny rules take precedence over allow rules.
    """
    # Check against deny list first
    for denied_cmd in COMMAND_DENY_LIST:
        if command.startswith(denied_cmd):
            return False
    # Check against allow list
    for allowed_cmd in COMMAND_ALLOW_LIST:
        if command.startswith(allowed_cmd):
            return True
    return False # Default to deny if not explicitly allowed

def execute_terminal_command(command: str) -> Tuple[str, str, int]:
    """
    Executes a shell command if it is allowed and returns its output, error, and return code.

    Args:
        command (str): The command to execute.

    Returns:
        Tuple[str, str, int]: A tuple containing stdout, stderr, and the return code.
                              If the command is not allowed, returns structured error info in stderr
                              and a non-zero return code.
    """
    if not is_command_allowed(command):
        command_name = command.split()[0] if command else ''
        error_info = f"COMMAND_NOT_ALLOWED|{command_name}|{command}"
        print(f"Command not allowed: {command}")
        return "", error_info, -1 # Indicate command not allowed

    try:
        # shlex.split is used to handle quoted arguments correctly
        args = shlex.split(command)
        process = subprocess.run(
            args,
            capture_output=True,
            text=True,
            check=False, # Do not raise an exception for non-zero exit codes
            timeout=30  # Add a timeout for safety
        )
        return process.stdout, process.stderr, process.returncode
    except FileNotFoundError:
        error_info = f"COMMAND_NOT_FOUND|{args[0]}|{command}"
        print(f"Command not found: {args[0]}")
        return "", error_info, -2 # Indicate command not found
    except subprocess.TimeoutExpired:
        error_info = f"COMMAND_TIMEOUT|{command}|30"
        print(f"Command timed out: {command}")
        return "", error_info, -3 # Indicate timeout
    except Exception as e:
        error_info = f"COMMAND_ERROR|{command}|{str(e)}"
        print(f"Error executing command: {command} - {e}")
        return "", error_info, -4 # Indicate other execution error

# Attach metadata for tool discovery
execute_terminal_command.name = "execute_terminal_command"
execute_terminal_command.description = "Executes a shell command if allowed, returning stdout, stderr, and return code. Error info in stderr uses format: ERROR_TYPE|context|details"
execute_terminal_command.args_schema = {
    "type": "object",
    "properties": {
        "command": {"type": "string"}
    },
    "required": ["command"]
}

if __name__ == '__main__':
    # Example usage:
    allowed_command = "ls -la"
    denied_command_prefix = "rm -rf /"
    denied_command_exact = "sudo reboot"
    non_existent_command = "myfantasycommand"
    allowed_echo = '''echo "Hello World with spaces"'''

    print(f"Executing: '{allowed_command}'")
    stdout, stderr, rc = execute_terminal_command(allowed_command)
    print(f"STDOUT:\n{stdout}")
    print(f"STDERR:\n{stderr}")
    print(f"Return Code: {rc}\n---")

    print(f"Executing: '{allowed_echo}'")
    stdout, stderr, rc = execute_terminal_command(allowed_echo)
    print(f"STDOUT:\n{stdout}")
    print(f"STDERR:\n{stderr}")
    print(f"Return Code: {rc}\n---")

    print(f"Attempting to execute: '{denied_command_prefix}'")
    stdout, stderr, rc = execute_terminal_command(denied_command_prefix)
    print(f"STDOUT:\n{stdout}")
    print(f"STDERR:\n{stderr}")
    print(f"Return Code: {rc}\n---")

    print(f"Attempting to execute: '{denied_command_exact}'")
    stdout, stderr, rc = execute_terminal_command(denied_command_exact)
    print(f"STDOUT:\n{stdout}")
    print(f"STDERR:\n{stderr}")
    print(f"Return Code: {rc}\n---")
    
    print(f"Attempting to execute: '{non_existent_command}'")
    stdout, stderr, rc = execute_terminal_command(non_existent_command)
    print(f"STDOUT:\n{stdout}")
    print(f"STDERR:\n{stderr}")
    print(f"Return Code: {rc}\n---")

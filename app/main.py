# main.py
from app.server.routes import app
from app.ui import AquariusUI
from multiprocessing import Process
import sys
import socket
import os
from app.config_manager import configManager


def start_api():
    # Determine API port from environment or config
    port = int(os.getenv("API_PORT", configManager.config.get("api_port", 5000)))
    try:
        app.run(port=port)
    except OSError as e:
        print(f"Unable to start Flask API on port {port}: {e}")
        sys.exit(1)


def main():
    """Launch the Flask API and Gradio UI."""

    api_proc = Process(target=start_api)
    api_proc.daemon = True
    api_proc.start()

    AquariusUI.launch_ui()


if __name__ == "__main__":
    main()

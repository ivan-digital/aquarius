# main.py
from app.server.routes import app
from app.ui import AquariusUI
from multiprocessing import Process
import sys
import socket
import os
from app.config_manager import configManager


def start_api(port):
    import atexit
    import asyncio
    from app.server.chat import ChatService
    
    # Create a chat service reference for cleanup
    chat_service = None
    for rule in app.url_map.iter_rules():
        if hasattr(app.view_functions.get(rule.endpoint, {}), '__closure__'):
            for cell in app.view_functions.get(rule.endpoint).__closure__ or []:
                if hasattr(cell, 'cell_contents') and isinstance(cell.cell_contents, ChatService):
                    chat_service = cell.cell_contents
                    break
    
    # Register cleanup function to ensure resources are properly released
    def cleanup_resources():
        print("Flask shutting down, cleaning up resources...")
        if chat_service:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(chat_service.close_agent_resources())
                loop.close()
                print("Chat service resources cleaned up successfully")
            except Exception as e:
                print(f"Error during cleanup: {e}")
    
    atexit.register(cleanup_resources)
    
    # Start Flask app
    print(f"Attempting to start Flask app on 0.0.0.0:{port}")
    try:
        app.run(host='0.0.0.0', port=port, debug=False) # Ensure host and disable debug for production-like setup
    except OSError as e:
        print(f"OSError when starting Flask API on port {port}: {e}") # Enhanced log
        sys.exit(1)
    except Exception as e: # Catch other potential exceptions
        print(f"Unexpected error when starting Flask API on port {port}: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Aquarius Application Launcher")
    parser.add_argument("--component", choices=["api", "ui", "all"], default=os.getenv("APP_COMPONENT", "all"),
                        help="Specify which component to run: api, ui, or all (default: all or APP_COMPONENT env var)")
    parser.add_argument("--port", type=int, default=os.getenv("PORT"),
                        help="Port for the specified component (API or UI). Overrides default/config.")
    parser.add_argument("--api_url", type=str, default=os.getenv("API_URL", configManager.get("api_url", "http://127.0.0.1:5002/api/chat")),
                        help="URL for the API service, used by the UI component.")
    parser.add_argument("--test-mode", action="store_true", help="Enable test mode")
    parser.add_argument("--api-only", action="store_true", help="Run in API-only mode (for testing)")

    args = parser.parse_args()

    # Set environment variables for test mode
    if args.test_mode:
        os.environ["TEST_MODE"] = "true"
        print("Test mode enabled - using lightweight LLM for tests")
    if args.api_only:
        args.component = "api"
        print("API-only mode enabled")

    # Set APP_COMPONENT globally if provided via CLI, as other modules might read it directly from os.environ
    # This ensures consistency if main.py is the entry point that defines it.
    if args.component:
        os.environ["APP_COMPONENT"] = args.component

    api_port = configManager.get("api_port", 5002)
    ui_port = configManager.get("ui_port", 7860)

    if args.component == "api":
        api_actual_port = args.port if args.port else api_port
        print(f"API component selected. Target port: {api_actual_port}") # ADD THIS
        print(f"Starting API server on port {api_actual_port}...")
        start_api(api_actual_port)
    elif args.component == "ui":
        ui_actual_port = args.port if args.port else ui_port
        AquariusUI.CHAT_API_URL = args.api_url # Override CHAT_API_URL for UI
        print(f"Starting UI server on port {ui_actual_port}, connecting to API at {args.api_url}...")
        AquariusUI.launch_ui(server_port=ui_actual_port)
    elif args.component == "all":
        api_actual_port = api_port # Use default/config for 'all' mode, CLI --port would be ambiguous
        ui_actual_port = ui_port

        print(f"ALL component selected. API target port: {api_actual_port}") # ADD THIS
        print(f"Starting API server on port {api_actual_port} as a background process...")
        api_proc = Process(target=start_api, args=(api_actual_port,))
        api_proc.daemon = True
        api_proc.start()

        # Ensure API has a moment to start before UI tries to connect if defaults are used
        # This is a simple delay; a more robust solution would be health checks.
        if args.api_url == f"http://127.0.0.1:{api_actual_port}/api/chat": # Basic check if UI is targeting local API
            time.sleep(3) 

        AquariusUI.CHAT_API_URL = args.api_url # Override CHAT_API_URL for UI
        print(f"Starting UI server on port {ui_actual_port}, connecting to API at {args.api_url}...")
        AquariusUI.launch_ui(server_port=ui_actual_port)
    else:
        print(f"Invalid component: {args.component}")
        sys.exit(1)

if __name__ == "__main__":
    import argparse # Moved import here
    import time # Moved import here
    main()

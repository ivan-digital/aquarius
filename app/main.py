# main.py
import threading
from app.server.routes import app
from app.ui import AquariusUI


def start_api():
    app.run(port=5000)


def main():
    api_thread = threading.Thread(target=start_api)
    api_thread.daemon = True
    api_thread.start()

    AquariusUI.launch_ui()


if __name__ == "__main__":
    main()

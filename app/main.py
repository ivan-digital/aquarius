# main.py
from app.server.routes import app
from app.ui import AquariusUI
from multiprocessing import Process


def start_api():
    app.run(port=5000)


def main():
    api_proc = Process(target=start_api)
    api_proc.daemon = True
    api_proc.start()

    AquariusUI.launch_ui()


if __name__ == "__main__":
    main()

class LogService:
    def __init__(self):
        self.logs = []

    def add_log(self, message: str):
        print(message)
        self.logs.append(message)

    def get_logs(self):
        return self.logs


log_service = LogService()

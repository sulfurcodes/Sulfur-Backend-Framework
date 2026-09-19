STATUS_MESSAGES = {
    200: "OK",
    201: "Created",
    204: "No Content",
    400: "Bad Request",
    404: "Not Found",
    405: "Method Not Allowed",
    500: "Internal Server Error",
}

class Response:
    def __init__(self, status_code = '404 Missing Not Found', text = 'Route Not Found') -> None:
        self.status_code = status_code
        self.text = text
        self.headers = []

    def as_wsgi(self, start_response):
        start_response(self.status_code, headers = self.headers)
        return [self.text.encode()]

    def send(self, text="", status_code=200):
        self.text = text if isinstance(text, str) else str(text)
        if isinstance(status_code, int):
            message = STATUS_MESSAGES.get(status_code)
            if message is None:
                raise ValueError(f"Unsupported status code: {status_code}")
            self.status_code = f"{status_code} {message}"
        elif isinstance(status_code, str):
            self.status_code = status_code
        else:
            raise ValueError("Status code must be an Integer or String")
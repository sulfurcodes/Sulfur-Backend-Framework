import json as _json

_STATUS_TEXT = {
    200: "OK", 201: "Created", 204: "No Content",
    301: "Moved Permanently", 302: "Found", 304: "Not Modified",
    400: "Bad Request", 401: "Unauthorized", 403: "Forbidden",
    404: "Not Found", 405: "Method Not Allowed",
    422: "Unprocessable Entity", 500: "Internal Server Error",
}


class Response:
    """WSGI response wrapper with dict backward-compat + upstream send/as_wsgi API."""

    def __init__(self, body="", status=200, headers=None, content_type="text/plain",
                 status_code=None, text=None):
        # upstream compat: Response(status_code='...', text='...')
        if status_code is not None and status == 200:
            status = self._parse_status(status_code)
        self.status = status
        self.headers = list(headers) if headers else []
        self._body = b""
        self._content_type_set = False
        if text is not None and not body:
            body = text
        if body is not None:
            self.set_body(body, content_type)

    # -- body helpers --
    def set_body(self, body, content_type=None):
        if isinstance(body, (dict, list)):
            self.json(body)
            return
        if isinstance(body, str):
            self._body = body.encode("utf-8")
        elif isinstance(body, bytes):
            self._body = body
        elif body is None:
            self._body = b""
        else:
            self._body = str(body).encode("utf-8")
        if content_type and not self._content_type_set:
            self.set_header("Content-Type", content_type)

    @property
    def text(self) -> str:
        return self._body.decode("utf-8", errors="replace")

    @text.setter
    def text(self, value):
        self.set_body(value if value is not None else "")

    def json(self, data, status=None):
        self._body = _json.dumps(data).encode("utf-8")
        self.set_header("Content-Type", "application/json")
        if status is not None:
            self.status = status
        return self

    @classmethod
    def json_response(cls, data, status=200):
        return cls(body="", status=status).json(data)

    def set_header(self, name, value):
        lname = name.lower()
        self.headers = [(k, v) for k, v in self.headers if k.lower() != lname]
        self.headers.append((name, value))
        if lname == "content-type":
            self._content_type_set = True

    # -- upstream API: res.send(text, status) + res.as_wsgi(start_response) --
    def send(self, text="", status_code="200 OK"):
        if isinstance(text, (dict, list)):
            self.json(text)
        elif isinstance(text, bytes):
            self._body = text
        else:
            self.text = text if isinstance(text, str) else str(text)
        self.status = self._parse_status(status_code)
        return self

    def as_wsgi(self, start_response):
        status, headers, body = self.to_wsgi()
        start_response(status, headers)
        return body

    # -- WSGI --
    @property
    def status_line(self) -> str:
        text = _STATUS_TEXT.get(self.status, "OK")
        return f"{self.status} {text}"

    @property
    def status_code(self) -> str:
        # upstream expects string like '200 OK'
        return self.status_line

    @status_code.setter
    def status_code(self, value):
        self.status = self._parse_status(value)

    @staticmethod
    def _parse_status(value):
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            try:
                return int(value.split()[0])
            except (ValueError, IndexError):
                return 200
        try:
            return int(value)
        except (ValueError, TypeError):
            return 200

    def to_wsgi(self):
        headers = list(self.headers)
        if not any(k.lower() == "content-type" for k, _ in headers):
            headers.append(("Content-Type", "text/plain"))
        return self.status_line, headers, [self._body]

    # -- backward compat: res["status_code"], res["headers"], res["text"] --
    def __getitem__(self, key):
        if key == "status_code":
            return self.status_line
        if key == "headers":
            return self.headers
        if key == "text":
            return self.text
        raise KeyError(key)

    def __setitem__(self, key, value):
        if key == "status_code":
            self.status = self._parse_status(value)
        elif key == "headers":
            self.headers = list(value) if value else []
        elif key == "text":
            if isinstance(value, (dict, list)):
                self.json(value)
            else:
                self.text = value if value is not None else ""
        else:
            raise KeyError(key)

import json as _json

_STATUS_TEXT = {
    200: "OK", 201: "Created", 204: "No Content",
    301: "Moved Permanently", 302: "Found", 304: "Not Modified",
    400: "Bad Request", 401: "Unauthorized", 403: "Forbidden",
    404: "Not Found", 405: "Method Not Allowed",
    422: "Unprocessable Entity", 500: "Internal Server Error",
}


class Response:
    """WSGI response wrapper with dict backward-compat for old handlers."""

    def __init__(self, body="", status=200, headers=None, content_type="text/plain"):
        self.status = status
        self.headers = list(headers) if headers else []
        self._body = b""
        self._content_type_set = False
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

    # -- WSGI --
    @property
    def status_line(self) -> str:
        text = _STATUS_TEXT.get(self.status, "OK")
        return f"{self.status} {text}"

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
            if isinstance(value, int):
                self.status = value
            elif isinstance(value, str):
                try:
                    self.status = int(value.split()[0])
                except (ValueError, IndexError):
                    self.status = 200
            else:
                self.status = int(value)
        elif key == "headers":
            self.headers = list(value) if value else []
        elif key == "text":
            if isinstance(value, (dict, list)):
                self.json(value)
            else:
                self.text = value if value is not None else ""
        else:
            raise KeyError(key)

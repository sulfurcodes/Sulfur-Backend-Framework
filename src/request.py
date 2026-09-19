import json as _json
from urllib.parse import parse_qs
from io import BytesIO


class Request:
    """WSGI request wrapper. Most useful boost: no more raw environ dicts."""

    def __init__(self, environ):
        self.environ = environ
        self.method = environ.get("REQUEST_METHOD", "GET").upper()
        self.path = environ.get("PATH_INFO", "/") or "/"
        self.query_string = environ.get("QUERY_STRING", "")
        # ?a=1&a=2 -> {"a": ["1", "2"]}, flattened to single value when len==1
        raw_qs = parse_qs(self.query_string, keep_blank_values=True)
        self.query_params = {k: v[0] if len(v) == 1 else v for k, v in raw_qs.items()}
        self.headers = self._parse_headers(environ)
        self.path_params = {}
        self._body = None
        self._json_cache = None

    @staticmethod
    def _parse_headers(environ):
        headers = {}
        for key, value in environ.items():
            if key.startswith("HTTP_"):
                name = key[5:].replace("_", "-").title()
                headers[name] = value
        # Content-Type / Content-Length are not HTTP_ prefixed
        if "CONTENT_TYPE" in environ and environ["CONTENT_TYPE"]:
            headers["Content-Type"] = environ["CONTENT_TYPE"]
        if "CONTENT_LENGTH" in environ and environ["CONTENT_LENGTH"]:
            headers["Content-Length"] = environ["CONTENT_LENGTH"]
        return headers

    @property
    def body(self) -> bytes:
        if self._body is None:
            stream = self.environ.get("wsgi.input", BytesIO(b""))
            try:
                length = int(self.environ.get("CONTENT_LENGTH") or 0)
            except (ValueError, TypeError):
                length = 0
            self._body = stream.read(length) if length > 0 else stream.read()
        return self._body or b""

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")

    def json(self):
        if self._json_cache is None:
            if not self.body:
                return None
            self._json_cache = _json.loads(self.text)
        return self._json_cache

    # upstream compat: handlers receiving environ dict can also accept Request
    def __getitem__(self, key):
        return self.environ[key]

    def get(self, key, default=None):
        return self.environ.get(key, default)

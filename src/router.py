import re

_PARAM_PATTERNS = [
    (re.compile(r"<int:(\w+)>"), r"(?P<\1>\\d+)"),
    (re.compile(r"<(\w+)>"), r"(?P<\1>[^/]+)"),
    (re.compile(r"\{(\w+)\}"), r"(?P<\1>[^/]+)"),
    (re.compile(r":(\w+)"), r"(?P<\1>[^/]+)"),
]


class Router:
    def __init__(self) -> None:
        # list of {template, regex, param_names, methods: {METHOD: handler}}
        self._routes = []

    # keep old attribute name working: {path: {METHOD: handler}}
    @property
    def routes(self):
        d = {}
        for r in self._routes:
            d.setdefault(r["template"], {}).update(r["methods"])
        return d

    def _compile(self, template):
        pattern = template
        # escape regex chars except our param syntax pieces handled below
        # do param replacement first on raw template
        regex = pattern
        for pat, repl in _PARAM_PATTERNS:
            regex = pat.sub(repl, regex)
        regex = f"^{regex.rstrip('/') or '/'}/?$"
        # normalize // edge: root "/" stays "^/?$"
        if template == "/":
            regex = r"^/?$"
        param_names = re.findall(r"\?P<(\w+)>", regex)
        return re.compile(regex), param_names

    def add(self, path, handler, methods):
        template = path or f"/{handler.__name__}"
        compiled, param_names = self._compile(template)
        # merge if same template exists
        for r in self._routes:
            if r["template"] == template:
                for m in methods:
                    r["methods"][m.upper()] = handler
                return handler
        self._routes.append({
            "template": template,
            "regex": compiled,
            "param_names": param_names,
            "methods": {m.upper(): handler for m in methods},
        })
        return handler

    def route(self, path=None, methods=None):
        methods = [m.upper() for m in (methods or ["GET"])]

        def wrapper(handler):
            return self.add(path, handler, methods)
        return wrapper

    def get(self, path=None):
        return self.route(path, methods=["GET"])

    def post(self, path=None):
        return self.route(path, methods=["POST"])

    def put(self, path=None):
        return self.route(path, methods=["PUT"])

    def patch(self, path=None):
        return self.route(path, methods=["PATCH"])

    def delete(self, path=None):
        return self.route(path, methods=["DELETE"])

    def match(self, method, path):
        """Returns (handler, path_params) or (None, {}) — plus 405 detection via match_any_method."""
        if not path:
            path = "/"
        allowed = set()
        for r in self._routes:
            m = r["regex"].match(path)
            if m:
                allowed.update(r["methods"].keys())
                if method.upper() in r["methods"]:
                    params = {k: v for k, v in m.groupdict().items()}
                    # coerce <int:name> params
                    if "<int:" in r["template"]:
                        for k in list(params.keys()):
                            if f"<int:{k}>" in r["template"]:
                                try:
                                    params[k] = int(params[k])
                                except ValueError:
                                    pass
                    return r["methods"][method.upper()], params
        return None, {"_allowed": allowed} if allowed else {}

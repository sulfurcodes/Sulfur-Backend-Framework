import re

_PARAM_PATTERNS = [
    (re.compile(r"<int:(\w+)>"), r"(?P<\1>\\d+)"),
    (re.compile(r"<(\w+)>"), r"(?P<\1>[^/]+)"),
    (re.compile(r"\{(\w+)\}"), r"(?P<\1>[^/]+)"),
    (re.compile(r":(\w+)"), r"(?P<\1>[^/]+)"),
]


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


class Router:
    """Merged router: regex path params (no external dep) + per-route middleware (upstream)."""

    def __init__(self) -> None:
        # list of {template, regex, param_names, methods: {METHOD: handler}, middlewares: {METHOD: [...]}}
        self._routes = []

    # dict view for backward compat: {path: {METHOD: handler}}
    @property
    def routes(self):
        d = {}
        for r in self._routes:
            d.setdefault(r["template"], {}).update(r["methods"])
        return d

    # upstream compat: {path: {METHOD: [middlewares]}}
    @property
    def middleware_for_routes(self):
        d = {}
        for r in self._routes:
            d.setdefault(r["template"], {}).update(r.get("middlewares", {}))
        return d

    def _compile(self, template):
        regex = template
        for pat, repl in _PARAM_PATTERNS:
            regex = pat.sub(repl, regex)
        regex = f"^{regex.rstrip('/') or '/'}/?$"
        if template == "/":
            regex = r"^/?$"
        param_names = re.findall(r"\?P<(\w+)>", regex)
        return re.compile(regex), param_names

    def add(self, path, handler, methods, middlewares=None):
        template = path or f"/{handler.__name__}"
        mw_list = _as_list(middlewares)
        compiled, param_names = self._compile(template)
        for r in self._routes:
            if r["template"] == template:
                for m in methods:
                    r["methods"][m.upper()] = handler
                    r.setdefault("middlewares", {})[m.upper()] = mw_list
                return handler
        self._routes.append({
            "template": template,
            "regex": compiled,
            "param_names": param_names,
            "methods": {m.upper(): handler for m in methods},
            "middlewares": {m.upper(): list(mw_list) for m in methods},
        })
        return handler

    # upstream compat name
    def commonMethod(self, path, handler, method_name, middlewares):
        return self.add(path, handler, [method_name], middlewares)

    def route(self, path=None, methods=None, middleware=None, middlewares=None):
        methods = [m.upper() for m in (methods or ["GET"])]
        mw = _as_list(middleware) + _as_list(middlewares)

        def wrapper(handler):
            return self.add(path, handler, methods, mw)
        return wrapper

    def get(self, path=None, middleware=None, middlewares=None):
        return self.route(path, methods=["GET"],
                          middleware=middleware, middlewares=middlewares)

    def post(self, path=None, middleware=None, middlewares=None):
        return self.route(path, methods=["POST"],
                          middleware=middleware, middlewares=middlewares)

    def put(self, path=None, middleware=None, middlewares=None):
        return self.route(path, methods=["PUT"],
                          middleware=middleware, middlewares=middlewares)

    def patch(self, path=None, middleware=None, middlewares=None):
        return self.route(path, methods=["PATCH"],
                          middleware=middleware, middlewares=middlewares)

    def delete(self, path=None, middleware=None, middlewares=None):
        return self.route(path, methods=["DELETE"],
                          middleware=middleware, middlewares=middlewares)

    def match(self, method, path):
        """Returns (handler, path_params, route_middlewares) or (None, {...}, [])."""
        if not path:
            path = "/"
        allowed = set()
        for r in self._routes:
            m = r["regex"].match(path)
            if m:
                allowed.update(r["methods"].keys())
                if method.upper() in r["methods"]:
                    params = {k: v for k, v in m.groupdict().items()}
                    if "<int:" in r["template"]:
                        for k in list(params.keys()):
                            if f"<int:{k}>" in r["template"]:
                                try:
                                    params[k] = int(params[k])
                                except ValueError:
                                    pass
                    route_mw = r.get("middlewares", {}).get(method.upper(), [])
                    return r["methods"][method.upper()], params, list(route_mw)
        if allowed:
            return None, {"_allowed": allowed}, []
        return None, {}, []

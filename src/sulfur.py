import types
from .router import Router
from .request import Request
from .response import Response


class Sulfur:
    """Merged app: upstream global+route middlewares and POST/DELETE,
    plus Request/Response objects, full REST verbs, path params,
    use()/before/after hooks, CORS/logger, and 404/405/500 handling."""

    def __init__(self, middlewares=None) -> None:
        self.router = Router()
        # upstream style: Sulfur(middlewares=[fn]) where fn(environ)
        self.middlewares = list(middlewares) if middlewares else []
        self._not_found_handler = None
        self._error_handler = None
        self._exception_handlers = {}

    # -- route decorators (support both `middleware=` and `middlewares=`) --
    def get(self, path=None, middleware=None, middlewares=None):
        mw = _as_list(middleware) + _as_list(middlewares)
        return self.router.get(path, middlewares=mw or None)

    def post(self, path=None, middleware=None, middlewares=None):
        mw = _as_list(middleware) + _as_list(middlewares)
        return self.router.post(path, middlewares=mw or None)

    def put(self, path=None, middleware=None, middlewares=None):
        mw = _as_list(middleware) + _as_list(middlewares)
        return self.router.put(path, middlewares=mw or None)

    def patch(self, path=None, middleware=None, middlewares=None):
        mw = _as_list(middleware) + _as_list(middlewares)
        return self.router.patch(path, middlewares=mw or None)

    def delete(self, path=None, middleware=None, middlewares=None):
        mw = _as_list(middleware) + _as_list(middlewares)
        return self.router.delete(path, middlewares=mw or None)

    def route(self, path=None, methods=None, middleware=None, middlewares=None):
        mw = _as_list(middleware) + _as_list(middlewares)
        return self.router.route(path, methods=methods, middlewares=mw or None)

    # -- middleware + error hooks --
    def use(self, mw):
        """Register middleware. Styles:
        - upstream: mw(environ)
        - chain: mw(req, res, next) -> return next() or Response to short-circuit.
        """
        if not isinstance(mw, types.FunctionType):
            raise ValueError("You can only pass functions as middlewares")
        self.middlewares.append(mw)
        return mw

    def before_request(self, fn):
        def wrapper(req, res, next):
            out = fn(req) if _arity(fn) <= 1 else fn(req, res)
            if out is not None:
                return self._coerce_result(out, res)
            return next()
        self.middlewares.append(wrapper)
        return fn

    def after_request(self, fn):
        def wrapper(req, res, next):
            resp = next()
            out = fn(req, resp)
            return out if out is not None else resp
        self.middlewares.append(wrapper)
        return fn

    def set_404(self, handler):
        self._not_found_handler = handler
        return handler

    def set_error(self, handler):
        self._error_handler = handler
        return handler

    def add_exception_handler(self, exc_class, handler):
        self._exception_handlers[exc_class] = handler
        return handler

    def __call__(self, environ, start_response) -> any:
        req = Request(environ)
        res = Response()

        def dispatch():
            return self._dispatch_route(req, res, environ)

        try:
            final = self._run_chain(0, req, res, environ, dispatch)
        except Exception as exc:
            final = self._handle_error(req, res, exc)
        # support both Response APIs
        if hasattr(final, "as_wsgi"):
            try:
                return final.as_wsgi(start_response)
            except TypeError:
                pass
        status, headers, body = final.to_wsgi()
        start_response(status, headers)
        return body

    # -- internals --
    def _dispatch_route(self, req, res, environ):
        matched = self.router.match(req.method, req.path)
        handler, path_params, route_mw = matched if len(matched) == 3 else (*matched, [])
        req.path_params = path_params if handler else {}

        if handler is None:
            allowed = (path_params or {}).get("_allowed", set())
            if allowed:
                tmp = Response()
                tmp.status = 405
                tmp.json({"error": f"Method {req.method} not allowed", "allowed": sorted(allowed)})
                return tmp
            if self._not_found_handler:
                try:
                    out = self._invoke(self._not_found_handler, req, res, {})
                    return self._coerce_result(out, res)
                except Exception as exc:
                    return self._handle_error(req, res, exc)
            tmp = Response(status=404)
            tmp.json({"error": f"Route {req.path} not found"})
            return tmp

        # per-route middlewares (upstream style mw(environ) or chain style)
        for mw in route_mw:
            try:
                self._invoke_mw_simple(mw, req, res, environ)
            except Exception as exc:
                return self._handle_error(req, res, exc)

        route_res = Response()
        try:
            result = self._invoke(handler, req, route_res, path_params)
            # upstream handlers mutate res via send() and return None
            if result is None and (route_res._body or route_res.status != 200):
                return route_res
            return self._coerce_result(result, route_res)
        except Exception as exc:
            return self._handle_error(req, route_res, exc)

    def _run_chain(self, idx, req, res, environ, dispatch):
        if idx >= len(self.middlewares):
            return dispatch()
        mw = self.middlewares[idx]
        box = {}

        def next_fn():
            try:
                r = self._run_chain(idx + 1, req, res, environ, dispatch)
            except Exception as exc:
                r = self._handle_error(req, res, exc)
            box["v"] = r
            return r

        # upstream 1-arg mw(environ): run for side effects, auto-continue
        if _is_upstream_mw(mw):
            mw(environ)
            return next_fn()

        out = self._invoke_mw(mw, req, res, next_fn)
        if out is None:
            if "v" in box:
                return box["v"]
            return self._run_chain(idx + 1, req, res, environ, dispatch)
        return self._coerce_result(out, out if isinstance(out, Response) else res)

    def _handle_error(self, req, res, exc):
        for exc_class, h in self._exception_handlers.items():
            try:
                if isinstance(exc, exc_class):
                    out = h(req, exc) if _arity(h) >= 2 else h(req)
                    return self._coerce_result(out, res)
            except Exception:
                pass
        if self._error_handler:
            try:
                out = self._error_handler(req, exc) if _arity(self._error_handler) >= 2 else self._error_handler(req)
                return self._coerce_result(out, res)
            except Exception:
                pass
        err = Response()
        err.status = 500
        err.json({"error": "Internal Server Error", "detail": str(exc)})
        return err

    @staticmethod
    def _invoke(handler, req, res, path_params=None):
        """Supports handler(req), handler(req,res), handler(req,res,**params),
        and legacy handler(environ, res_dict). Request supports environ access."""
        import inspect
        path_params = path_params or {}
        try:
            sig = inspect.signature(handler)
            params = list(sig.parameters.values())
        except (ValueError, TypeError):
            return handler(req, res)
        n = len(params)
        names = [p.name for p in params]
        # upstream style with path kwargs: def getUsers(req, res, id)
        if n >= 3 or (n == 2 and any(k in names for k in path_params)):
            kwargs = {k: v for k, v in path_params.items() if k in names}
            if n >= 3 and len(kwargs) < len(path_params):
                # pass all path params positionally/by name fallback
                kwargs = dict(path_params)
            try:
                return handler(req, res, **kwargs)
            except TypeError:
                pass
        if n <= 1:
            return handler(req)
        return handler(req, res)

    @staticmethod
    def _invoke_mw_simple(mw, req, res, environ):
        # per-route mw: prefer mw(environ), else mw(req), mw(req,res), chain style
        n = _arity(mw)
        import inspect
        try:
            names = list(inspect.signature(mw).parameters.keys())
        except (ValueError, TypeError):
            names = []
        if n <= 1:
            try:
                return mw(environ)
            except Exception:
                return mw(req)
        if n == 2 and "next" not in names:
            try:
                return mw(req, res)
            except Exception:
                return mw(environ, res)
        # chain style without next_fn here: give auto-next that returns None
        return mw(req, res, lambda: None)

    @staticmethod
    def _invoke_mw(mw, req, res, next_fn):
        import inspect
        try:
            sig = inspect.signature(mw)
            params = list(sig.parameters.values())
        except (ValueError, TypeError):
            return mw(req, res, next_fn)
        n = len(params)
        has_next = any(p.name == "next" for p in params)
        if n >= 3 or (n == 2 and has_next):
            return mw(req, res, next_fn)
        if n == 2:
            if params[1].name == "next":
                return mw(req, next_fn)
            return mw(req, res)
        if n == 1:
            if params[0].name == "next":
                return next_fn()
            return mw(req)
        return mw()

    @staticmethod
    def _coerce_result(result, res: Response) -> Response:
        if result is None:
            return res
        if isinstance(result, Response):
            return result
        if isinstance(result, tuple) and len(result) == 2 and isinstance(result[1], int):
            body, status = result
            res.status = status
            result = body
        if isinstance(result, (dict, list)):
            res.json(result)
            return res
        if isinstance(result, bytes):
            res.set_body(result, content_type="application/octet-stream")
            return res
        res.set_body(result if isinstance(result, str) else str(result))
        return res


def _arity(fn):
    import inspect
    try:
        return len(inspect.signature(fn).parameters)
    except (ValueError, TypeError):
        return 2


def _is_upstream_mw(mw):
    import inspect
    try:
        params = list(inspect.signature(mw).parameters.values())
    except (ValueError, TypeError):
        return False
    return len(params) == 1 and params[0].name in ("request", "environ", "req", "environment")


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]

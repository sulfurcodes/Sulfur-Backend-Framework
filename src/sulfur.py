from .router import Router
from .request import Request
from .response import Response


class Sulfur:
    def __init__(self) -> None:
        self.router = Router()
        self.middlewares = []
        self._not_found_handler = None
        self._error_handler = None
        self._exception_handlers = {}

    # -- route decorators (full REST verbs) --
    def get(self, path=None):
        return self.router.get(path)

    def post(self, path=None):
        return self.router.post(path)

    def put(self, path=None):
        return self.router.put(path)

    def patch(self, path=None):
        return self.router.patch(path)

    def delete(self, path=None):
        return self.router.delete(path)

    def route(self, path=None, methods=None):
        return self.router.route(path, methods=methods)

    # -- middleware + error hooks (boost #1) --
    def use(self, mw):
        """Register middleware. Styles supported:
        mw(req, res, next) -> return next() or return Response to short-circuit.
        Also supports mw(req, res), mw(req, next), mw(req) (auto-continues if returns None).
        """
        self.middlewares.append(mw)
        return mw

    def before_request(self, fn):
        """Simple before-hook: fn(req) -> return Response to block, else None to continue."""
        def wrapper(req, res, next):
            out = fn(req) if _arity(fn) <= 1 else fn(req, res)
            if out is not None:
                return self._coerce_result(out, res)
            return next()
        self.middlewares.append(wrapper)
        return fn

    def after_request(self, fn):
        """Simple after-hook: fn(req, resp) -> resp (may mutate)."""
        def wrapper(req, res, next):
            resp = next()
            out = fn(req, resp)
            return out if out is not None else resp
        self.middlewares.append(wrapper)
        return fn

    def set_404(self, handler):
        """Custom 404: handler(req) -> anything coercible."""
        self._not_found_handler = handler
        return handler

    def set_error(self, handler):
        """Custom 500: handler(req, exc) -> anything coercible."""
        self._error_handler = handler
        return handler

    def add_exception_handler(self, exc_class, handler):
        """Handler for specific exception: handler(req, exc) -> anything."""
        self._exception_handlers[exc_class] = handler
        return handler

    def __call__(self, environ, start_response) -> any:
        req = Request(environ)
        res = Response()

        def dispatch():
            return self._dispatch_route(req, res)

        try:
            final = self._run_chain(0, req, res, dispatch)
        except Exception as exc:
            final = self._handle_error(req, res, exc)
        status, headers, body = final.to_wsgi()
        start_response(status, headers)
        return body

    # -- internals --
    def _dispatch_route(self, req, res):
        handler, path_params = self.router.match(req.method, req.path)
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
                    out = self._invoke(self._not_found_handler, req, res)
                    return self._coerce_result(out, res)
                except Exception as exc:
                    return self._handle_error(req, res, exc)
            tmp = Response()
            tmp.status = 404
            tmp.json({"error": f"Route {req.path} not found"})
            return tmp

        # fresh response per request (don't leak headers across requests)
        route_res = Response()
        try:
            result = self._invoke(handler, req, route_res)
            return self._coerce_result(result, route_res)
        except Exception as exc:
            # return (not raise) so middleware post-processing (CORS, logging)
            # still runs as the chain unwinds
            return self._handle_error(req, route_res, exc)

    def _run_chain(self, idx, req, res, dispatch):
        if idx >= len(self.middlewares):
            return dispatch()
        mw = self.middlewares[idx]
        box = {}

        def next_fn():
            try:
                r = self._run_chain(idx + 1, req, res, dispatch)
            except Exception as exc:
                # inner middleware/route raised: convert to error response
                # so outer middleware can still post-process (e.g. CORS headers)
                r = self._handle_error(req, res, exc)
            box["v"] = r
            return r

        out = self._invoke_mw(mw, req, res, next_fn)
        if out is None:
            # auto-continue for before-style middleware that returned None
            if "v" in box:
                return box["v"]
            return self._run_chain(idx + 1, req, res, dispatch)
        coerced = self._coerce_result(out, out if isinstance(out, Response) else res)
        # if middleware called next() but also returned None-ish wrapper, prefer next result?
        # _invoke_mw returns next result directly when mw returns next()'s value, so coerced is correct.
        # Edge: mw called next() internally but returned None -> handled above via box.
        return coerced if not isinstance(out, Response) or True else out

    def _handle_error(self, req, res, exc):
        # specific exception handlers first (isinstance walk)
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
    def _invoke(handler, req, res):
        """Supports handler(req) / handler(req, res) and legacy handler(environ, res_dict)."""
        n = _arity(handler)
        if n <= 1:
            return handler(req)
        return handler(req, res)

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
            # could be (req, res) or (req, next) — decide by name
            if params[1].name == "next":
                return mw(req, next_fn)
            return mw(req, res)
        if n == 1:
            name = params[0].name
            if name == "next":
                return next_fn()
            return mw(req)
        return mw()

    @staticmethod
    def _coerce_result(result, res: Response) -> Response:
        """Allows: return str | dict | list | bytes | Response | None (uses mutated res)."""
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

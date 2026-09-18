import time


def logger(handler=None):
    """Request logger middleware. Usage: app.use(logger())."""
    import sys
    log = handler or (lambda msg: print(msg, file=sys.stdout))

    def middleware(req, res, next):
        start = time.perf_counter()
        try:
            resp = next()
        finally:
            pass
        # resp is a Response here (chain guarantees it)
        try:
            status = getattr(resp, "status", "?")
            ms = (time.perf_counter() - start) * 1000
            log(f"{req.method} {req.path} -> {status} ({ms:.1f}ms)")
        except Exception:
            pass
        return resp

    return middleware


def cors(allow_origins="*", allow_methods="GET, POST, PUT, PATCH, DELETE, OPTIONS",
         allow_headers="Content-Type, Authorization", max_age="86400"):
    """CORS middleware. Adds headers to every response, short-circuits OPTIONS."""
    from .response import Response

    if isinstance(allow_origins, (list, tuple)):
        allow_origins_val = ", ".join(allow_origins)
    else:
        allow_origins_val = allow_origins

    def middleware(req, res, next):
        # preflight: short-circuit, no route needed
        if req.method.upper() == "OPTIONS":
            r = Response(status=204)
            r.set_header("Access-Control-Allow-Origin", allow_origins_val)
            r.set_header("Access-Control-Allow-Methods", allow_methods)
            r.set_header("Access-Control-Allow-Headers", allow_headers)
            r.set_header("Access-Control-Max-Age", str(max_age))
            r.set_header("Content-Length", "0")
            return r
        resp = next()
        # attach to actual route response (resp is Response)
        try:
            resp.set_header("Access-Control-Allow-Origin", allow_origins_val)
            resp.set_header("Access-Control-Allow-Methods", allow_methods)
            resp.set_header("Access-Control-Allow-Headers", allow_headers)
        except Exception:
            pass
        return resp

    return middleware


def powered_by(name="Sulfur"):
    def middleware(req, res, next):
        resp = next()
        try:
            resp.set_header("X-Powered-By", name)
        except Exception:
            pass
        return resp
    return middleware

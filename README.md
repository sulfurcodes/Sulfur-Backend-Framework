# Sulfur

A lightweight Python backend framework built from scratch to learn how web frameworks work internally — WSGI, routing, requests/responses, and middleware.

## Description

Sulfur exposes a minimal Express/Flask-style API on top of raw WSGI:

- Define routes with decorators (`@app.get/post/put/patch/delete`)
- Path params (`/users/{id}`, `/users/:id`, `/users/<id>`, `/users/<int:id>`), query parsing, JSON bodies
- `Request` / `Response` objects, plus backward-compatible dict and `res.send()` APIs
- Global middleware (`Sulfur(middlewares=[...])`, `app.use(...)`) and per-route middleware (`middleware=[...]`)
- Built-ins: request logger, CORS (with `OPTIONS` preflight), `X-Powered-By`
- `before_request` / `after_request` hooks, custom 404 / 500 handlers, per-exception handlers
- Proper `404 Not Found`, `405 Method Not Allowed`, and `500` JSON errors instead of hanging

## Installation

```bash
git clone https://github.com/sulfurcodes/Sulfur-Backend-Framework.git
cd Sulfur-Backend-Framework
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install gunicorn
```

No framework dependencies for core routing (stdlib only).

## Quickstart

```python
from src.sulfur import Sulfur
from src.response import Response

app = Sulfur()

@app.get("/users/{id}")
def get_user(req):
    return {"id": req.path_params["id"]}

@app.post("/users")
def create_user(req):
    return Response.json_response({"created": req.json()}, status=201)
```

Run with:

```bash
gunicorn examples.app:app --reload
# or: gunicorn example.app:app --reload
```

## Routing

```python
@app.get("/users") ...
@app.post("/users") ...
@app.put("/users/{id}") ...
@app.patch("/users/{id}") ...
@app.delete("/users") ...
@app.route("/custom", methods=["GET", "POST"]) ...
```

Path params support `{id}`, `:id`, `<id>`, `<int:id>` (int-coerced). Matched values land in `req.path_params`, or as handler kwargs:

```python
# upstream style — also supported
def getUsers(req, res, id):
    res.send(f"GET Route with id {id}", 200)

app.get("/users/{id}", middleware=[getMiddleware])(getUsers)
```

Query strings: `req.query_params` (`/search?q=hello` → `{"q": "hello"}`).

## Request / Response

```python
req.method, req.path, req.query_params, req.headers
req.path_params, req.body, req.text, req.json()
req["PATH_INFO"]  # environ access still works
```

Handlers may:

- `return {"key": "value"}` / `return [...]` → auto JSON
- `return "text"` / `return b"bytes"` / `return (body, 201)`
- `return Response.json_response(data, status=201)`
- mutate `res` (`res.send("hi", 200)`, `res.json(...)`, or legacy `res["text"] = ...`) and return `None`

## Middleware

```python
from src.middleware import logger, cors, powered_by

app = Sulfur(middlewares=[globalMiddleware])  # upstream style: fn(environ)
app.use(logger())   # chain style: fn(req, res, next)
app.use(cors())     # adds Access-Control-* + handles OPTIONS → 204
app.use(powered_by("Sulfur"))

@app.before_request
def auth(req):
    if req.path.startswith("/admin"):
        return Response.json_response({"error": "Unauthorized"}, status=401)

@app.after_request
def version(req, resp):
    resp.set_header("X-Api-Version", "0.2")
    return resp
```

Per-route middleware runs before the handler:

```python
app.get("/users/{id}", middleware=[getMiddleware])(getUsers)
app.post("/users", middleware=[postMiddleware])(postUsers)
```

Chain order: first registered = outermost (`m1-before → m2-before → handler → m2-after → m1-after`). Returning a `Response` without calling `next()` short-circuits.

## Errors

- Unknown path → `404 {"error": "Route /x not found"}`
- Wrong method → `405 {"error": "...", "allowed": [...]}`
- Exception → `500 {"error": "Internal Server Error", "detail": "..."}`

Customize:

```python
@app.set_404
def not_found(req):
    return Response.json_response({"error": f"{req.path} missing"}, status=404)

@app.set_error
def on_crash(req, exc):
    return Response.json_response({"error": "boom"}, status=500)

app.add_exception_handler(ValueError, lambda req, exc: {"error": str(exc)})
```

## Project structure

```text
Sulfur-Backend-Framework/
├── example/            # upstream style: controllers + per-route middleware
│   ├── app.py
│   ├── controllers.py
│   └── middlewares.py
├── examples/
│   └── app.py          # full-stack demo: logger/CORS/auth/version/JSON/500
├── src/
│   ├── sulfur.py       # app, middleware chain, error handling
│   ├── router.py       # regex routing + per-route middleware
│   ├── request.py      # Request wrapper
│   ├── response.py     # Response wrapper (+ send/as_wsgi compat)
│   ├── middleware.py   # logger, cors, powered_by
│   └── __init__.py
└── tests/
```

## What changed in this PR

Merged two parallel tracks that conflicted (`origin/main` added POST/DELETE + global/route middlewares with the `parse` lib; this branch added Request/Response + full REST + chain middleware + CORS/logger + 404/405/500):

- `src/response.py`: kept JSON/status/headers/dict API, added upstream `send(text, status)` + `as_wsgi(start_response)` + `status_code` string alias — both example styles work.
- `src/router.py`: kept stdlib regex params (`{id}`, `:id`, `<id>`, `<int:id>`) instead of `parse`, added `middleware_for_routes` + `middleware=`/`middlewares=` on all verbs + `PUT`/`PATCH`/`route()`.
- `src/sulfur.py`: `Sulfur(middlewares=[...])` + `app.use/before_request/after_request`, runs both `mw(environ)` and `mw(req,res,next)` styles, supports `handler(req)`, `handler(req,res)`, and `handler(req,res,id)` path-kwarg style; route errors return (not raise) so CORS/logging still apply.
- `src/request.py`: added `req["KEY"]` / `req.get()` environ access for old handlers.
- Kept both `example/` (upstream) and `examples/app.py` (new demo) instead of delete-vs-modify.
- Verified: `GET /users/42 → 200`, `POST /users → 201`, `DELETE → 200`, `GET /nope → 404`, wrong method → `405`, `OPTIONS → 204` with CORS, exception → `500` with CORS headers, middleware order intact.

## Goal

Sulfur is primarily a learning project — build a backend framework from scratch while understanding WSGI, routing, and server architecture. More features will be added as it evolves.

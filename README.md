# Sulfur

A lightweight backend framework built from scratch with Python.

Sulfur is an educational backend framework created to explore how web frameworks work internally. It is built from the ground up to understand concepts such as WSGI, HTTP request handling, routing, and server architecture.

## Current Features

* WSGI application interface
* Basic HTTP request handling
* Route registration
* `GET` routes
* Development reload support with Gunicorn

## Example

```python
from src.sulfur import Sulfur

app = Sulfur()

@app.get("/users")
def getUsers(req, res):
    res["status_code"] = "200 OK"
    res["headers"] = []
    res["text"] = "Sulfurcodes"
```

Run the application with:

```bash
gunicorn examples.app:app --reload
```

## Project Structure

```text
Sulfur Framework/
├── examples/
│   └── app.py
├── src/
│   ├── sulfur.py
│   └── router.py
└── ...
```

## Goal

Sulfur is primarily a learning project. The goal is to build a backend framework from scratch while understanding the concepts and architecture behind modern Python web frameworks.

More features will be added as the framework evolves.

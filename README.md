# Sulfur

A lightweight backend framework built from scratch with Python.

Sulfur is an educational project focused on understanding how backend frameworks work internally — from WSGI and HTTP handling to routing, middleware, and response processing.

## Current Features

* WSGI application interface
* HTTP request handling through the WSGI `environ`
* Route registration
* `GET`, `POST`, and `DELETE` routes
* Dynamic route parameters
* Global middleware
* Route-specific middleware
* Basic response abstraction
* Gunicorn development reload support

## Example

```python
from src.sulfur import Sulfur

app = Sulfur()


@app.get("/users/{id}")
def get_user(req, res, id):
    res.send(f"User ID: {id}", 200)


@app.post("/users")
def create_user(req, res):
    res.send("User created", 201)


@app.delete("/users")
def delete_user(req, res):
    res.send("User deleted", 200)
```

## Middleware

Sulfur supports both global and route-specific middleware.

### Global Middleware

```python
def logger(environ):
    print("Request received")


app = Sulfur(middlewares=[logger])
```

### Route-Specific Middleware

```python
def auth(environ):
    print("Checking authentication")


@app.get("/users/{id}", middleware=[auth])
def get_user(req, res, id):
    res.send(f"User ID: {id}", 200)
```

## Running the Example

Create and activate a virtual environment, install the dependencies, then run:

```bash
gunicorn example.app:app --reload
```

The example application demonstrates routing, path parameters, middleware, and responses.

## Project Structure

```text
Sulfur-Backend-Framework/
├── example/
│   ├── app.py
│   ├── controllers.py
│   └── middlewares.py
├── sulfur/
│   ├── __init__.py
│   ├── request.py
│   ├── response.py
│   ├── router.py
│   └── main.py
├── .gitignore
└── LICENSE
```
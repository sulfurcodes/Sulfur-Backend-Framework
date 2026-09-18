from src.sulfur import Sulfur
from src.response import Response
from src.middleware import logger, cors, powered_by

app = Sulfur()

# -- middleware stack (order matters: first registered = outermost) --
app.use(logger())
app.use(cors())
app.use(powered_by("Sulfur"))

# simple auth example: block /admin without token
@app.before_request
def auth(req):
    if req.path.startswith("/admin") and req.headers.get("Authorization") != "Bearer secret":
        return Response.json_response({"error": "Unauthorized"}, status=401)
    return None

@app.after_request
def add_version(req, resp):
    resp.set_header("X-Api-Version", "0.2")
    return resp

@app.set_404
def not_found(req):
    return Response.json_response({"error": f"{req.path} missing", "hint": "try /users"}, status=404)

@app.set_error
def on_crash(req, exc):
    return Response.json_response({"error": "boom", "detail": str(exc)}, status=500)

# legacy style still works (backward compat)
@app.get('/users')
def getUsers(req, res):
    res['status_code'] = '200 OK'
    res['headers'] = []
    res['text'] = 'Sulfurcodes'

# new style: return dict -> auto JSON
@app.get('/api/users/{id}')
def get_user(req):
    return {"id": req.path_params.get("id"), "name": "Sulfurcodes"}

@app.get('/search')
def search(req):
    # /search?q=hello -> {"q": "hello"}
    return {"q": req.query_params.get("q", "")}

@app.post('/api/users')
def create_user(req):
    data = req.json() or {}
    return Response.json_response({"created": data}, status=201)

@app.get('/boom')
def boom(req):
    raise ValueError("kaboom")

# gunicorn examples.app:app --reload

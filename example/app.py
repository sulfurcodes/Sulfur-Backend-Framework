from sulfur import Sulfur
from .controllers import getUsers, postUsers, deleteUsers
from .middlewares import globalMiddleware, getMiddleware, postMiddleware, deleteMiddleware

app = Sulfur(middlewares=[globalMiddleware])

app.get('/users/{id}', middleware=[getMiddleware])(getUsers)
app.post('/users', middleware=[postMiddleware])(postUsers)
app.delete('/users', middleware=[deleteMiddleware])(deleteUsers)

# source venv/bin/activate
# gunicorn example.app:app --reload
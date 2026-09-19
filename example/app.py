from sulfur import Sulfur
from .controllers import getUsers, postUsers, deleteUsers, getUsersById, getQueries
from .middlewares import globalMiddleware, getMiddleware, postMiddleware, deleteMiddleware

app = Sulfur(middlewares=[globalMiddleware])

app.get('/users', middleware=[getMiddleware])(getUsers)
app.post('/users', middleware=[postMiddleware])(postUsers)
app.delete('/users', middleware=[deleteMiddleware])(deleteUsers)

app.get('/user/{id}', middleware=[getMiddleware])(getUsersById)
app.get('/user', middleware=[getMiddleware])(getQueries)


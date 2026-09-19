def getUsers(req, res):
    res.send(f'GET Route', 200)

def postUsers(req, res):
    res.send('POST Route', 201)

def deleteUsers(req, res):
    res.send('DELETE Route', 200)

def getUsersById(req, res, id):
    res.send(f'User with Id: {id}')

def getQueries(req, res):
    name = req.query['name']
    age = req.query['age']
    res.send(f"Name: {name}, Age: {age}", 200)
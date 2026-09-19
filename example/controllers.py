def getUsers(req, res, id):
    res.send(f'GET Route with id {id}', 200)

def postUsers(req, res):
    res.send('POST Route', 201)

def deleteUsers(req, res):
    res.send('DELETE Route', 200)
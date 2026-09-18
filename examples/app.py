from src.sulfur import Sulfur

app = Sulfur()

@app.get('/users')
def getUsers(req, res):
    res['status_code'] = '200 OK'
    res['headers'] = []
    res['text'] = 'Sulfurcodes'

# gunicorn examples.app:app --reload
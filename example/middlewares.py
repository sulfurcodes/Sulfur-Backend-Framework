def globalMiddleware(request):
    print('This was executed before any route')

def getMiddleware(request):
    print('This was executed before GET route')

def postMiddleware(request):
    print('This was executed before POST route')

def deleteMiddleware(request):
    print('This was executed before DELETE route')
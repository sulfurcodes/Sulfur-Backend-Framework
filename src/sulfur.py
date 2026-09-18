from .router import Router

class Sulfur:
    def __init__(self) -> None:
        self.router = Router()

    def get(self, path=None):
            return self.router.get(path)

    def __call__(self, environ, start_response) -> any:
        reponse = {}
        for path, handler_dict in self.router.routes.items():
            for request_method, handler in handler_dict.items():
                if environ['PATH_INFO'] == path and environ['REQUEST_METHOD'] == request_method:
                    handler(environ, reponse)
                    start_response(reponse['status_code'], headers = reponse['headers'])
                    return [(reponse['text']).encode()]

    
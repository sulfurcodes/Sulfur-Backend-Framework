import types
from parse import parse
from .router import Router
from .response import Response
from .request import Request

class Sulfur:
    def __init__(self, middlewares = None) -> None:
        self.router = Router()
        self.middlewares = middlewares or []

    def get(self, path=None, middleware = None):
        return self.router.get(path, middleware)
    
    def post(self, path=None, middleware = None):
        return self.router.post(path, middleware)
    
    def delete(self, path=None, middleware = None):
        return self.router.delete(path, middleware)
    
    def __call__(self, environ, start_response) -> any:
        response = Response()
        request = Request(environ)

        for middleware in self.middlewares:
            if isinstance(middleware, types.FunctionType):
                middleware(request)
            else:
                raise ValueError('You can only pass functions as middlewares')

        for path, handler_dict in self.router.routes.items():
            route = parse(path, request.path_info)
            for request_method, handler in handler_dict.items():
                if route and request.request_method == request_method:
                    route_mw_list = self.router.middleware_for_routes[path][request_method]
                    for mw in route_mw_list:
                        if isinstance(mw, types.FunctionType):
                            mw(request)
                        else:
                            raise ValueError('You can only pass functions as middlewares')
                    handler(request, response, **route.named)
                    return response.as_wsgi(start_response)
        response.send('Route Not Found', 404)        
        return response.as_wsgi(start_response)
    
class Router:
    def __init__(self) -> None:
        self.routes = dict()
        self.middleware_for_routes = {}

    def commonMethod(self, path, handler, method_name, middlewares):
        path_name = path or f'/{handler.__name__}'

        if path_name not in self.routes:
            self.routes[path_name] = {}
        self.routes[path_name][method_name] = handler

        if path_name not in self.middleware_for_routes:
            self.middleware_for_routes[path_name] = {}
        self.middleware_for_routes[path_name][method_name] = middlewares or []

        return handler

    def get(self, path=None, middlewares=None):
        def wrapper(handler):
            return self.commonMethod(path, handler, 'GET', middlewares)
        return wrapper

    def post(self, path=None, middlewares=None):
        def wrapper(handler):
            return self.commonMethod(path, handler, 'POST', middlewares)
        return wrapper

    def delete(self, path=None, middlewares=None):
        def wrapper(handler):
            return self.commonMethod(path, handler, 'DELETE', middlewares)
        return wrapper
class Router:
    def __init__(self) -> None:
        self.routes = dict()

    def get(self, path=None):
            def wrapper(handler):
                path_name = path or f'/{handler.__name__}'
                if path_name not in self.routes:
                    self.routes[path_name] = {}
                self.routes[path_name]['GET'] = handler
                return handler
            return wrapper
    
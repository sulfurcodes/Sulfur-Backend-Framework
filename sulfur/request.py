from urllib.parse import parse_qs

class Request:
    def __init__(self, environ) -> None:
        for key, val in environ.items():
            setattr(self, key.replace('.', '_').lower(), val)
        raw_query = environ.get('QUERY_STRING', '')
        parsed = parse_qs(raw_query, keep_blank_values=True)
        self.query = {key: values[-1] for key, values in parsed.items()}
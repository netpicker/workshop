from requests import Request, Session


class SlurpitSession(Session):
    def __init__(self, url, token, ssl_verify):
        super().__init__()
        self.ssl_verify = ssl_verify
        self.headers.update(dict(authorization=token))
        self.base_api = url

    def prepare_request(self, request: Request):
        if ':/' not in request.url:
            glue = '' if request.url.startswith('/') else '/'
            request.url = glue.join((self.base_api, request.url))
        return super().prepare_request(request)

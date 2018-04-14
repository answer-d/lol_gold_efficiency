from django.http import HttpResponse
from django.conf import settings
import base64


class BasicAuthMiddleware(object):
    """環境変数「BASICAUTH_USERNAME」が存在する場合、アプリケーションにBasic認証をかけるMiddleware
    アカウントは「BASICAUTH_USERNAME」から、パスワードは「BASICAUTH_PASSWORD」から拾うぞ"""

    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        response = self.process_request(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response

    @staticmethod
    def unauthed():
        response = HttpResponse("""<html><title>Auth required</title><body>
        <h1>Authorization Required</h1></body></html""")
        response['WWW-Authenticate'] = 'Basic realm="Development"'
        response.status_code = 401
        return response

    def process_request(self, request):
        if settings.BASICAUTH_USERNAME is not None:
            if 'HTTP_AUTHORIZATION' not in request.META:
                return self.unauthed()
            else:
                authentication = request.META['HTTP_AUTHORIZATION']
                (authmeth, auth) = authentication.split(' ', 1)

                if 'basic' != authmeth.lower():
                    return self.unauthed()

                auth = base64.b64decode(auth.strip())
                username, password = auth.decode('utf-8').split(':', 1)

                if username == settings.BASICAUTH_USERNAME and password == settings.BASICAUTH_PASSWORD:
                    return self.get_response(request)

                return self.unauthed()
        else:
            return self.get_response(request)

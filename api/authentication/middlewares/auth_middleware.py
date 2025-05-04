import jwt
from django.conf import settings

class TokenMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            # Get token from cookies
            token = request.COOKIES.get('access_token')
            if token:
                try:
                    # Decode the token and add the data to request
                    decoded_token = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                    request.user_data = decoded_token
                except jwt.ExpiredSignatureError:
                    request.user_data = None
                except jwt.InvalidTokenError:
                    request.user_data = None
            else:
                request.user_data = None

            response = self.get_response(request)
            return response
        except Exception as e:
            print(f"Middleware error: {str(e)}")
            request.user_data = None
            return self.get_response(request)
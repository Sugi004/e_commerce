from django.contrib.auth.hashers import check_password
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
import json
from ..mongoDb import get_collection  
import jwt
from datetime import datetime, timedelta
from decouple import config
from django.shortcuts import render, redirect

def is_json_request(request):
    return request.content_type == 'application/json'

@csrf_exempt
def login_view(request):
    if request.method == "POST":
        try:
            if is_json_request(request):
                data = json.loads(request.body)
                email = data.get("email")
                password = data.get("password")
            else:
                email = request.POST.get("email", "").strip()
                password = request.POST.get("password", "").strip()

            if not email or not password:
                if is_json_request(request):
                    return JsonResponse({"error": "Email and password are required"}, status=400)
                messages.error(request, "Email and password are required")
                return render(request, 'login.html')

            user_collection = get_collection("users")
            user = user_collection.find_one({"email": email})

            if not user:
                if is_json_request(request):
                    return JsonResponse({"error": "Invalid credentials"}, status=401)
                messages.error(request, "Invalid credentials")
                return render(request, 'login.html')

            # Verify hashed password
            stored_hashed_password = user.get("password")
            if not check_password(password, stored_hashed_password):
                if is_json_request(request):
                    return JsonResponse({"error": "Invalid credentials"}, status=401)
                messages.error(request, "Invalid credentials")
                return render(request, 'login.html')

            # Create JWT payload
            payload = {
                "user_id": str(user["_id"]),
                "email": user["email"],
                "role": user.get("role", "guest"),
                "exp": datetime.now() + timedelta(hours=24)
            }

            # Generate JWT token
            secret_key = config('SECRET_KEY')
            token = jwt.encode(payload, secret_key, algorithm="HS256")

            # Set session data
            request.session["user_id"] = str(user["_id"])
            request.session["role"] = payload["role"]

            # Prepare response
            if is_json_request(request):
                response_data = {
                    "message": "Login successful",
                    "role": payload["role"],
                    "token": token
                }
                response = JsonResponse(response_data, status=200)
            else:
                messages.success(request, "Login successful")
                response = redirect("render_products")

            # Set cookie
            response.set_cookie(
                key="access_token",
                value=token,
                httponly=True,
                secure=True,
                samesite="Strict"
            )

            return response

        except json.JSONDecodeError:
            if is_json_request(request):
                return JsonResponse({"error": "Invalid JSON"}, status=400)
            messages.error(request, "Invalid JSON")
            return render(request, 'login.html')
        except Exception as e:
            if is_json_request(request):
                return JsonResponse({"error": str(e)}, status=500)
            messages.error(request, str(e))
            return render(request, 'login.html')

    return render(request, 'login.html')

def logout_view(request):
    request.session.flush()
    response = redirect('render_products')
    response.delete_cookie('access_token')
    messages.success(request, "Logged out successfully")
    return response

def sign_up(request):
    return render(request, 'sign_up.html')
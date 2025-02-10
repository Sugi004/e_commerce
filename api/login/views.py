from django.contrib.auth.hashers import check_password
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from ..mongoDb import get_collection  
import jwt
from datetime import datetime, timedelta
from decouple import config
from django.shortcuts import render, redirect


@csrf_exempt
def login_view(request):
    if request.method == "POST":
        try:
            is_jsonRequest = request.content_type == 'application/json'
            if is_jsonRequest:
                data = json.loads(request.body)
                email = data.get("email")
                password = data.get("password")
            else:
                # Handle form submission
                email = request.POST.get("email", "").strip()
                password = request.POST.get("password", "").strip()

            if not email or not password:
                return JsonResponse({"error": "Email and password are required"}, status=400)

            user_collection = get_collection("users")

            # Fetch user by email
            user = user_collection.find_one({"email": email})

            if not user:
                return JsonResponse({"error": "Invalid credentials"}, status=401)

            # Verify hashed password
            stored_hashed_password = user.get("password")
            if not check_password(password, stored_hashed_password):
                return JsonResponse({"error": "Invalid credentials"}, status=401)

            # Determine user role
            payload = {
                "user_id": str(user["_id"]),  # Use MongoDB's _id as user identifier
                "email": user["email"],
                "role": user.get("role", "guest"), 
                "exp": datetime.now() + timedelta(hours=24)  # Set token expiration to 24 hours
            }

            # Generate the JWT token
            secret_key =  config('SECRET_KEY')
            algorithm = "HS256"  # Algorithm to sign the token

            token = jwt.encode(payload, secret_key, algorithm=algorithm)
        
            # Prepare response with the generated token
            response = {
                "message": "Login successful",
                "role": payload["role"]
            }

            request.session["user_id"] = str(user["_id"])
            request.session["role"] = payload["role"]

            if is_jsonRequest:
                response_data = {
                    "message": "Login successful",
                    "role": payload["role"],
                    "token": token
                }
                response = JsonResponse(response_data, status=200)
            else:
                response = redirect("/products/")

            #Store the token in cookie for future
            response.set_cookie(
                key="access_token",
                value=token,
                httponly=True,
                secure=True,
                samesite="Strict"
            )

            return response 
            

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return render(request, 'login.html')

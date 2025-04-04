from django.http import JsonResponse
from django.shortcuts import redirect
from django.contrib import messages
from api.mongoDb import get_collection
from .userSchema import UserSchema
from django.contrib.auth.hashers import make_password
import json
import jwt
from decouple import config
from datetime import datetime
from marshmallow import ValidationError
from bson import ObjectId
from ..cart_management.cart_management_db import transfer_guest_cart


users_collection = get_collection("users")

def is_json_request(request):
    return request.content_type == "application/json"

def get_users(request):
    """Admin API to get all users using token stored in cookies under 'auth_token'"""
    token = request.COOKIES.get("auth_token").split(" ")[1]
    if not token:
        if is_json_request(request):
            return JsonResponse({"error": "Authorization token required"}, status=401)
        else:
            messages.error(request, "Authorization token required")
            return redirect("render_products")
    try:
        # Decode the JWT token from cookies
        decoded_token = jwt.decode(token, config("SECRET_KEY"), algorithms=["HS256"])
        # Check if the role is admin
        if decoded_token.get("role") != "admin":
            if is_json_request(request):
                return JsonResponse({"error": "Access denied, admin role required"}, status=403)
            else:
                messages.error(request, "Access denied, admin role required")
                return redirect("render_products")
        # Fetch all users if admin role
        users = list(users_collection.find())
        # Remove sensitive information before returning
        for user in users:
            user["_id"] = str(user["_id"])
            if "password" in user:
                del user["password"]

        if is_json_request(request):
            return JsonResponse({"users": users}, status=200)
        else:
            messages.success(request, "Users retrieved successfully")
            return redirect("render_products")

    except jwt.ExpiredSignatureError:
        error_msg = "Token has expired"
    except jwt.InvalidTokenError:
        error_msg = "Invalid token"
    except Exception as e:
        error_msg = str(e)

    if is_json_request(request):
        return JsonResponse({"error": error_msg}, status=401)
    else:
        messages.error(request, error_msg)
        return redirect("render_products")


def create_user(request):
    """API to create a new user. Returns JSON if the request is JSON, otherwise uses messages and redirects."""
    if request.method == "POST":
        try:
            if is_json_request(request):
                if request.body:
                    data = json.loads(request.body)
                else:
                    return JsonResponse({"error": "Empty request body"}, status=400)
            else:
                data = request.POST.dict()
                data.pop("csrfmiddlewaretoken", None)

            schema = UserSchema()
            validated_data = schema.load(data)
            validated_data["role"] = validated_data.get("role", "customer")

            if users_collection.find_one({"email": validated_data["email"]}):
                error_msg = "Email already exists"
                if is_json_request(request):
                    return JsonResponse({"error": error_msg}, status=400)
                else:
                    messages.error(request, error_msg)
                    return redirect("sign_up")
            if users_collection.find_one({"name": validated_data["name"]}):
                error_msg = "Name already exists"
                if is_json_request(request):
                    return JsonResponse({"error": error_msg}, status=400)
                else:
                    messages.error(request, error_msg)
                    return redirect("sign_up")
            if validated_data["role"] == "admin" and users_collection.count_documents({"role": "admin"}) >= 3:
                error_msg = "Only a maximum of 3 admin users are allowed"
                if is_json_request(request):
                    return JsonResponse({"error": error_msg}, status=400)
                else:
                    messages.error(request, error_msg)
                    return redirect("sign_up")
            old_session_id = request.session.session_key


            validated_data["password"] = make_password(validated_data["password"])
            validated_data["created_at"] = datetime.utcnow()
            if old_session_id:
                validated_data["session_id"] = old_session_id
            users_collection.insert_one(validated_data)
            success_msg = (
                "User created successfully"
                if is_json_request(request)
                else "User created successfully, please sign in."
            )
            if is_json_request(request):
                return JsonResponse({"message": success_msg}, status=201)
            else:
                messages.success(request, success_msg)
                return redirect("login_view")

        except ValidationError as err:
            if is_json_request(request):
                return JsonResponse({"error": err.messages}, status=400)
            else:
                messages.error(request, err.messages)
                return redirect("sign_up")
        except Exception as e:
            if is_json_request(request):
                return JsonResponse({"error": str(e)}, status=500)
            else:
                messages.error(request, str(e))
                return redirect("sign_up")

    if is_json_request(request):
        return JsonResponse({"error": "Invalid request method"}, status=405)
    else:
        messages.error(request, "Invalid request method")
        return redirect("sign_up")


def update_user(request, user_id):
    """Update user details (Admin-only: lock, suspend, role change)"""
    if request.method == "POST" and request.POST.get('_method') == 'PUT':
        try:
            if is_json_request(request):
                data = json.loads(request.body)
            else:
                data = request.POST.dict()

            update_data = {}
            if "is_locked" in data:
                update_data["is_locked"] = data["is_locked"]
            if "is_active" in data:
                update_data["is_active"] = data["is_active"].lower() == "true"
            if "role" in data:
                update_data["role"] = data["role"].lower()
            if "name" in data:
                update_data["name"] = data["name"]
            if "email" in data:
                update_data["email"] = data["email"]
            if "password" in data:
                update_data["password"] = make_password(data["password"])

            if not update_data:
                error_msg = "No valid fields to update"
                if is_json_request(request):
                    return JsonResponse({"error": error_msg}, status=400)
                else:
                    messages.error(request, error_msg)
                    return redirect("render_products")

            result = users_collection.update_one({"_id": ObjectId(user_id)}, {"$set": update_data})
            if result.matched_count == 0:
                error_msg = "User not found"
                if is_json_request(request):
                    return JsonResponse({"error": error_msg}, status=404)
                else:
                    messages.error(request, error_msg)
                    return redirect("render_products")

            success_msg = "User updated successfully"
            if is_json_request(request):
                return JsonResponse({"message": success_msg}, status=200)
            else:
                messages.success(request, success_msg)
                return redirect("render_products")

        except Exception as e:
            if is_json_request(request):
                return JsonResponse({"error": str(e)}, status=500)
            else:
                messages.error(request, str(e))
                return redirect("render_products")

    error_msg = "Invalid request method"
    if is_json_request(request):
        return JsonResponse({"error": error_msg}, status=405)
    else:
        messages.error(request, error_msg)
        return redirect("render_products")


def delete_user(request, user_id):
    """Delete a user (Admin-only)"""
    if request.method == 'POST' and request.POST.get('_method') == 'DELETE':
        try:
            result = users_collection.delete_one({"_id": ObjectId(user_id)})
            if result.deleted_count == 0:
                error_msg = "User not found"
                if is_json_request(request):
                    return JsonResponse({"error": error_msg}, status=404)
                else:
                    messages.error(request, error_msg)
                    return redirect("render_products")

            success_msg = "User deleted successfully"
            if is_json_request(request):
                return JsonResponse({"message": success_msg}, status=200)
            else:
                messages.success(request, success_msg)
                return redirect("render_products")

        except Exception as e:
            if is_json_request(request):
                return JsonResponse({"error": str(e)}, status=500)
            else:
                messages.error(request, str(e))
                return redirect("render_products")

    error_msg = "Invalid request method"
    if is_json_request(request):
        return JsonResponse({"error": error_msg}, status=405)
    else:
        messages.error(request, error_msg)
        return redirect("render_products")


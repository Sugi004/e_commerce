from ..checkout.views import send_verification_email
from django.conf import settings
import uuid
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.contrib import messages
from api.mongoDb import get_collection
from .userSchema import UserSchema
from django.contrib.auth.hashers import make_password
import json
import jwt
from decouple import config
from datetime import datetime, timedelta
from marshmallow import ValidationError
from bson import ObjectId
from django.views.decorators.csrf import csrf_exempt

users_collection = get_collection("users")

def is_json_request(request):
    return request.content_type == "application/json"

# For future if implementing API
# def get_users(request):
#     try:
#         # Fetch all users from the database
#         users = list(users_collection.find())

#         # Remove sensitive information before returning
#         for user in users:
#             user["id"] = str(user["_id"])  # Convert ObjectId to string
#             if "password" in user:
#                 del user["password"]  # Remove password for security

#         # Return users as JSON if the request is JSON
#         if is_json_request(request):
#             return JsonResponse({"users": users}, status=200)

#         # Otherwise, render the users page
#         return render(request, "users/users.html", {"users": users, "admin_name": request.user_data.get('email')})

#     except Exception as e:
#         # Handle errors and return appropriate responses
#         error_msg = str(e)
#         if is_json_request(request):
#             return JsonResponse({"error": error_msg}, status=500)
#         else:
#             messages.error(request, error_msg)
#             return redirect("render_products")


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
            validated_data.update({
            "role": validated_data.get("role", "customer"),
            "password": make_password(validated_data["password"]),
            "created_at": datetime.utcnow(),
            "loyalty_points": 0,
            "session_id": request.session.session_key if request.session.session_key else None
        })
             # Check for duplicate email or name
            if users_collection.find_one({"email": validated_data["email"]}) or users_collection.find_one({"name": validated_data["name"]}):
                error_msg = "Email or name already exists"
                if is_json_request(request):
                    return JsonResponse({"error": error_msg}, status=400)
                else:
                    messages.error(request, error_msg)
                    return redirect("sign_up")

            # Restrict admin creation to a maximum of 3
            if validated_data["role"] == "admin" and users_collection.count_documents({"role": "admin"}) >= 3:
                error_msg = "Only a maximum of 3 admin users are allowed"
                if is_json_request(request):
                    return JsonResponse({"error": error_msg}, status=400)
                else:
                    messages.error(request, error_msg)
                    return redirect("sign_up")
            old_session_id = request.session.session_key
            
            
            if old_session_id:
                validated_data["session_id"] = old_session_id\

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
                    return redirect("render_users_admin")

            result = users_collection.update_one({"_id": ObjectId(user_id)}, {"$set": update_data})
            if result.matched_count == 0:
                error_msg = "User not found"
                if is_json_request(request):
                    return JsonResponse({"error": error_msg}, status=404)
                else:
                    messages.error(request, error_msg)
                    return redirect("render_users_admin")

            success_msg = "User updated successfully"
            if is_json_request(request):
                return JsonResponse({"message": success_msg}, status=200)
            else:
                messages.success(request, success_msg)
                return redirect("render_users_admin")

        except Exception as e:
            if is_json_request(request):
                return JsonResponse({"error": str(e)}, status=500)
            else:
                messages.error(request, str(e))
                return redirect("render_users_admin")

    error_msg = "Invalid request method"
    if is_json_request(request):
        return JsonResponse({"error": error_msg}, status=405)
    else:
        messages.error(request, error_msg)
        return redirect("render_users_admin")


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

def verify_email(request, token, user_id):
    """Verify user email address"""
    try:

        if not token or not user_id:
            messages.error(request, "Invalid verification link")
            return redirect('login_view')

        # Find user with valid verification token
        user = users_collection.find_one({
            "verification_token": token,
            "verification_token_expires": {"$gt": datetime.utcnow()}
        })
        
        if not user:
            if is_json_request(request):
                return JsonResponse({"error": "Invalid or expired verification token"}, status=400)
            messages.error(request, "Invalid or expired verification token")
            return render(request, 'error.html')
            
        # Update user verification status
        users_collection.update_one(
            {"_id": user["_id"]},
            {
                "$set": {
                    "is_verified": True,
                },
                "$unset": {
                    "verification_token": "",
                    "verification_token_expires": ""
                }
            }
        )
        
        if is_json_request(request):
            return JsonResponse({"message": "Email verified successfully"}, status=200)
        
        request.session['user_data'] = {
            "user_id": str(user["_id"]),
            "email": user["email"],
            "role": user.get("role", "customer")
        }

        request.session.save()
        
        messages.success(request, "Email verified successfully. You can now complete your purchase.")
        return redirect('checkout')
        
    except Exception as e:
        if is_json_request(request):
            return JsonResponse({"error": str(e)}, status=500)
        messages.error(request, f"Verification failed: {str(e)}")
        return redirect("checkout")

@csrf_exempt
def resend_verification(request):
    """Resend verification email to user"""
    try:
        if not request.user_data:
            messages.error(request, "Please login to continue")
            return redirect('login_view')

        user = users_collection.find_one({"_id": ObjectId(request.user_data["user_id"])})
        
        if not user:
            messages.error(request, "User not found")
            return redirect('checkout')
            
        if user.get("is_verified"):
            messages.info(request, "Your email is already verified")
            return redirect('checkout')

        # Generate new verification token
        verification_token = str(uuid.uuid4())
        users_collection.update_one(
            {"_id": user["_id"]},
            {
                "$set": {
                    "verification_token": verification_token,
                    "verification_token_expires": datetime.utcnow() + timedelta(minutes=settings.EMAIL_VERIFICATION_TIMEOUT)
                }
            }
        )
        
        # Send verification email
        if send_verification_email(user["email"], verification_token):
            messages.success(request, "Verification email sent. Please check your inbox.")
        else:
            messages.error(request, "Failed to send verification email. Please try again.")
            
        return redirect('checkout')

    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect('checkout')


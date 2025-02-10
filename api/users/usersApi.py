from django.http import JsonResponse
from api.mongoDb import get_collection
from .userSchema import UserSchema
from django.contrib.auth.hashers import make_password
import json
import jwt
from decouple import config
from datetime import datetime
from marshmallow import ValidationError

users_collection = get_collection("users")


def get_users(request):
    """Admin API to get all users"""

    # Check for Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return JsonResponse({"error": "Authorization token required"}, status=401)

    try:
        # Extract the token (Bearer token)
        token = auth_header.split(" ")[1]  # Get the token after "Bearer"
        
        # Decode the JWT token
        decoded_token = jwt.decode(token, config("SECRET_KEY"), algorithms=["HS256"])

        # Check if the role is admin
        user_role = decoded_token.get("role")
        if user_role != "admin":
            return JsonResponse({"error": "Access denied, admin role required"}, status=403)

        # Fetch all users if admin role
        user_collection = get_collection("users")
        users = list(user_collection.find())

        # Remove password and other sensitive information before returning
        for user in users:
            user["_id"] = str(user["_id"])  # Convert ObjectId to string
            del user["password"]  # Remove password from the response

        return JsonResponse({"users": users}, status=200)

    except jwt.ExpiredSignatureError:
        return JsonResponse({"error": "Token has expired"}, status=401)
    except jwt.InvalidTokenError:
        return JsonResponse({"error": "Invalid token"}, status=401)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def get_user_by_id(request, user_id):
    """Fetch a single user by ID (Admin-only)"""
    if request.method == "GET":
        try:
            user = users_collection.find_one({"_id": user_id}, {"password": 0})  # Exclude password

            if not user:
                return JsonResponse({"error": "User not found"}, status=404)

            user["_id"] = str(user["_id"])  # Convert ObjectId to string
            return JsonResponse(user, status=200)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)

def create_user(request):
    """Admin API to create a new user"""
    if request.method == "POST":
        try:
            # Parse the request body
            data = json.loads(request.body)
            schema = UserSchema()
            validated_data = schema.load(data)
            validated_data["role"] = validated_data.get("role", "customer")

            # Check if the email or name already exists
            if users_collection.find_one({"email": validated_data["email"]}):
                return JsonResponse({"error": "Email already exists"}, status=400)

            if users_collection.find_one({"name": validated_data["name"]}):
                return JsonResponse({"error": "Name already exists"}, status=400)

            # Check if admin users count is more than 3
            if validated_data["role"] == "admin" and users_collection.count_documents({"role": "admin"}) >= 3:
                return JsonResponse({"error": "Only a maximum of 3 admin users are allowed"}, status=400)

            # Hash password before storing
            validated_data["password"] = make_password(validated_data["password"])

            # Add creation timestamp
            validated_data["created_at"] = datetime.utcnow()

            # Insert new user into the MongoDB collection
            users_collection.insert_one(validated_data)

            return JsonResponse({"message": "User created successfully"}, status=201)

        except ValidationError as err:
            return JsonResponse({"error": err.messages}, status=400)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)

def update_user(request, user_id):
    """Update user details (Admin-only: lock, suspend, role change)"""
    if request.method == "PUT":
        try:
            data = json.loads(request.body)
            update_data = {}

            if "is_locked" in data:
                update_data["is_locked"] = data["is_locked"]

            if "is_active" in data:
                update_data["is_active"] = data["is_active"]

            if "role" in data:
                update_data["role"] = data["role"].lower()

            if not update_data:
                return JsonResponse({"error": "No valid fields to update"}, status=400)

            # Update user in MongoDB
            result = users_collection.update_one({"_id": user_id}, {"$set": update_data})

            if result.matched_count == 0:
                return JsonResponse({"error": "User not found"}, status=404)

            return JsonResponse({"message": "User updated successfully"}, status=200)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)

def delete_user(request, user_id):
    """Delete a user (Admin-only)"""
    if request.method == "DELETE":
        try:
            result = users_collection.delete_one({"_id": user_id})

            if result.deleted_count == 0:
                return JsonResponse({"error": "User not found"}, status=404)

            return JsonResponse({"message": "User deleted successfully"}, status=200)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)


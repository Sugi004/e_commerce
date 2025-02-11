from django.shortcuts import render, redirect
from django.http import JsonResponse
from .usersApi import get_users
import logging
import json
from bson import ObjectId
from ..mongoDb import get_collection

users_collection = get_collection("users")

logger = logging.getLogger(__name__)

def render_users_admin(request):
    try:
        # Debug log to check user data
        logger.debug(f"User data: {request.user_data}")

        # Check if user is authenticated and has admin role
        if not request.user_data:
            return redirect('login_view')
        
        if request.user_data.get('role') != 'admin':
            return render(request, "error.html", {
                "error": "Access denied. Admin privileges required."
            })

        # Get token from cookies
        token = request.COOKIES.get('access_token')
        if not token:
            return redirect('login_view')

        # Add authorization header to the request
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {token}'

        # Fetch user data from the JSON API
        response = get_users(request)
        
        # Debug log for API response
        logger.debug(f"API Response: {response}")

        if isinstance(response, JsonResponse):
            users_data = json.loads(response.content.decode('utf-8'))
            
            # Get the users list from the response
            if isinstance(users_data, dict) and 'users' in users_data:
                users_list = users_data['users']
            else:
                users_list = users_data if isinstance(users_data, list) else [users_data]

            # Transform user data
            transformed_users = []
            for user in users_list:
                transformed_user = {
                    'id': str(user.get('_id', '')),
                    'name': user.get('name', ''),
                    'email': user.get('email', ''),
                    'role': user.get('role', ''),
                    'is_active': user.get('is_active', False),
                    'created_at': user.get('created_at', '')
                }
                transformed_users.append(transformed_user)


            return render(request, "users.html", {
                "users": transformed_users,
                "admin_name": request.user_data.get('email')
            })
        
        # If no valid response, show empty user list
        return render(request, "users.html", {
            "users": [],
            "admin_name": request.user_data.get('email'),
            "message": "No users found"
        })

    except Exception as e:
        logger.error(f"Error in render_users_admin: {str(e)}", exc_info=True)
        return render(request, "error.html", {
            "error": f"An error occurred: {str(e)}"
        })

def edit_user(request, user_id):
    try:
        user = users_collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            return render(request, "error.html", {"error": "User not found"})
        # Transform the ObjectId field
        user['id'] = str(user.get('_id'))
        return render(request, "edit_user.html", {
            "user": user,
            "admin_name": request.user_data.get('email')
        })
    except Exception as e:
        logger.error(f"Error in edit_user: {str(e)}", exc_info=True)
        return render(request, "error.html", {"error": str(e)})
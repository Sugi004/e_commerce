from django.shortcuts import render
from bson import ObjectId
from ..mongoDb import get_collection

users_collection = get_collection("users")

def render_users_admin(request):
    """Render the admin user management page."""
    try:
        # Check if the user is authenticated and has admin role
        if not request.user_data or request.user_data.get("role") != "admin":
            return render(request, "error.html", {
                "error": "Access denied. Admin privileges required."
            })

        # Fetch users from the database
        users = list(users_collection.find())

        transformed_users = []
        for user in users:
            transformed_user = {
                "id": str(user.get("_id", "")),  # Ensure 'id' is set correctly
                "name": user.get("name", ""),
                "email": user.get("email", ""),
                "role": user.get("role", ""),
                "is_active": user.get("is_active", False),
                "created_at": user.get("created_at", ""),
            }
            transformed_users.append(transformed_user)

        # Render the admin user management page
        return render(request, "users/users.html", {
            "users": transformed_users,
            "admin_name": request.user_data.get("email"),
        })

    except Exception as e:
        # Handle errors and render the error page
        return render(request, "error.html", {
            "error": f"An error occurred: {str(e)}"
        })

def edit_user(request, user_id):
    try:
        print("user_id", user_id)
        user = users_collection.find_one({"_id": ObjectId(user_id)})
        print("user", user)
         # Check if the user is authenticated and has admin role
        if not user:
            return render(request, "error.html", {"error": "User not found"})
        # Transform the ObjectId field
        user['id'] = str(user.get('_id'))
        return render(request, "users/edit_user.html", {
            "user": user,
            "admin_name": request.user_data.get('email')
        })
    except Exception as e:
        print(f"Error in edit_user: {str(e)}")
        return render(request, "error.html", {"error": str(e)})
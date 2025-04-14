from bson import ObjectId
from django.shortcuts import render, redirect
from django.contrib import messages
from ..mongoDb import get_collection
from datetime import datetime

users_collection = get_collection("users")

def edit_user(request, user_id):
    """View to edit user profile details."""
    try:
        # Fetch the user from the database
        user = users_collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            return render(request, "error.html", {"error": "User not found"})

        if request.method == "POST":
            # Update user details
            name = request.POST.get("name")
            email = request.POST.get("email")

            # Update the user in the database
            users_collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {
                    "name": name,
                    "email": email,
                    "updated_at": datetime.utcnow()
                }}
            )
            messages.success(request, "Profile updated successfully!")
            return redirect("profile_view", user_id=user_id)

        # Transform the ObjectId field for the template
        user["id"] = str(user["_id"])
        return render(request, "users/edit_user.html", {"user": user})

    except Exception as e:
        print(f"Error in edit_user: {str(e)}")
        return render(request, "error.html", {"error": str(e)})




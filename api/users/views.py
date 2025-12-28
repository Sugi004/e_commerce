from ..modules import *


def edit_user(request, user_id):
    try:
        user = users_collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            messages.error(request, "User not found.")
            return render(request, "error.html")
        # Transform the ObjectId field
        user['id'] = str(user.get('_id'))

        return render(request, "users/edit_user.html", {
            "user": user,
            "admin_name": request.user_data.get('email')
        })
    except Exception as e:
        print(f"Error in edit_user: {str(e)}")
        messages.error(request, "An error occurred while fetching user data.")
        return render(request, "error.html")
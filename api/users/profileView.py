from ..modules import *

def profile_view(request, user_id):
    if not user_id:
        return JsonResponse({"error": "User ID not found in URL"}, status=400)

    # Fetch user details
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    
    if not user:
        return render(request, "users/profile.html", {"error": "User not found"})

    # Fetch addresses for the user
    address_data = address_collection.find_one({"user_id": ObjectId(user_id)})
    addresses = address_data.get("addresses", []) if address_data else []

    return render(request, "users/profile.html", {"user": user, "addresses": addresses, "user_id": user_id})

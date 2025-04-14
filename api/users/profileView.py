from django.shortcuts import render
from ..mongoDb import get_collection
from bson import ObjectId
from django.http import JsonResponse

def profile_view(request, user_id):
    if not user_id:
        return JsonResponse({"error": "User ID not found in URL"}, status=400)
    
    user_collection = get_collection("users")
    address_collection = get_collection("addresses")

    # Fetch user details
    user = user_collection.find_one({"_id": ObjectId(user_id)})
    user['id'] = str(user['_id']) 
    
    if not user:
        return render(request, "users/profile.html", {"user_id": user_id})

    # Fetch addresses for the user
    address_data = address_collection.find_one({"user_id": ObjectId(user_id)})
    addresses = address_data.get("addresses", []) if address_data else []

    return render(request, "users/profile.html", {"user": user, "addresses": addresses})

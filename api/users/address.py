from ..modules import *
from .userSchema import AddressSchema

schema = AddressSchema()

def initialize_address_collection():    
    # Create compound index for user_id and address type
    # Unique constraint ensures one address type per user
    address_collection.create_index(
        [
            ("user_id", 1),
            ("addresses.type", 1)
        ],
        unique=True,
        partialFilterExpression={"addresses.type": {"$exists": True}}
    )
    
    return address_collection

@csrf_exempt
def add_address(request, user_id):
    if request.method == "GET":
        # Render the address form
        context = {"user_id": user_id}
        return render(request, "users/add_address.html", context)

    elif request.method == "POST":
        try:
            # Extract address data from the form
            address = {
                "type": request.POST.get("type"),
                "street": request.POST.get("street"),
                "city": request.POST.get("city"),
                "state": request.POST.get("state"),
                "zip": request.POST.get("zip"),
                "country": request.POST.get("country"),
                "phone": request.POST.get("phone"),
            }

            # Validate address using AddressSchema
            
            try:
                validated_address = schema.load(address)
            except ValidationError as e:
                messages.error(request, f"Validation error: {e.messages}")
                return redirect("profile_view", user_id=user_id)

            # Ensure the user exists
            user = users_collection.find_one({"_id": ObjectId(user_id)})
            if not user:
                messages.error(request, "User not found")
                return redirect("profile_view", user_id=user_id)

            # Add or update the address in the addresses collection
            try:
                address_collection.update_one(
                    {"user_id": ObjectId(user_id)},
                    {"$push": {"addresses": validated_address}},
                    upsert=True
                )
                messages.success(request, "Address added successfully")
                return redirect("profile_view", user_id=user_id)
            except Exception as e:
                if "duplicate key error" in str(e).lower():
                    # Update the existing address if it already exists
                    address_collection.update_one(
                        {
                            "user_id": ObjectId(user_id),
                            "addresses.type": validated_address["type"]
                        },
                        {"$set": {"addresses.$": validated_address}}
                    )
                    messages.success(request, "Address updated successfully")
                    return redirect("profile_view", user_id=user_id)
                raise

        except Exception as e:
            messages.error(request, f"Error adding address: {str(e)}")
            return redirect("profile_view", user_id=user_id)

    messages.error(request, "Invalid request method")
    return redirect("profile_view", user_id=user_id)

def get_user_profile(request, user_id):
    """Retrieve user profile and associated addresses."""
    try:
        # Fetch user details excluding the password
        user = users_collection.find_one({"_id": ObjectId(user_id)}, {"password": 0})
        if not user:
            messages.error(request, "User not found")
            return redirect("profile_view", user_id=user_id)

        # Fetch associated addresses
        addresses = list(address_collection.find(
            {"user_id": ObjectId(user_id)},
            {"_id": 0, "user_id": 0}
        ))

        # Prepare user data for rendering
        user_data = {
            "user_id": str(user["_id"]),
            "name": user.get("name"),
            "email": user.get("email"),
            "role": user.get("role", "customer"),
            "phone": user.get("phone", ""),
            "addresses": addresses,
            "created_at": user.get("created_at"),
            "updated_at": user.get("updated_at")
        }

        return render(request, 'users/profile.html', {'user_data': user_data})

    except Exception as e:
        messages.error(request, f"Error retrieving profile: {str(e)}")
        return redirect("profile_view", user_id=user_id)
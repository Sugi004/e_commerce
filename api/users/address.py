from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.shortcuts import redirect
import json
from ..mongoDb import get_collection
from bson import ObjectId
from marshmallow import ValidationError
from .userSchema import AddressSchema  # Import the schema


user_collection = get_collection("users")
address_collection = get_collection("addresses")

@csrf_exempt
def add_address(request, user_id):
    if request.method == "POST":
        try:
            is_json_request = request.content_type == "application/json"
            if is_json_request:
                data = json.loads(request.body)
                user_id = data.get("user_id")  # Extract user ID
                address = data.get("address")
            else:
                user_id = request.POST.get("user_id", "").strip()
                address = request.POST.get("address", "").strip()

            if not user_id or not address:
                return JsonResponse({"error": "User ID and address are required"}, status=400)

            # Validate address using AddressSchema
            schema = AddressSchema()
            validated_address = schema.load(address)  # Validate and deserialize

            # Ensure the user exists
            user_collection = get_collection("users")
            user = user_collection.find_one({"_id": ObjectId(user_id)})

            if not user:
                return JsonResponse({"error": "User not found"}, status=404)

            # Get the address collection
            address_collection = get_collection("addresses")

            # Check if the user already has an address
            existing_address = address_collection.find_one({"user_id": ObjectId(user_id)})

            if existing_address:
                # Check if the address type (e.g., Home/Work) already exists in the user's addresses
                address_list = existing_address.get("addresses", [])
                address_type_exists = any(addr["type"] == validated_address["type"] for addr in address_list)

                if address_type_exists:
                    # Update only the existing address of the same type
                    updated_addresses = [
                        addr if addr["type"] != validated_address["type"] else validated_address
                        for addr in address_list
                    ]
                else:
                    # Add the new address to the list
                    updated_addresses = address_list + [validated_address]

                # Update the existing document
                address_collection.update_one(
                    {"_id": existing_address["_id"]},
                    {"$set": {"addresses": updated_addresses}}
                )
                message = "Address updated successfully"
            else:
                # Insert new address if user has no address stored
                address_collection.insert_one({
                    "user_id": ObjectId(user_id),
                    "addresses": [validated_address]  # Store addresses as a list
                })
                message = "Address added successfully"

            return JsonResponse({"message": message}, status=201)

        except ValidationError as e:
            return JsonResponse({"error": e.messages}, status=400)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Method not allowed"}, status=405)


def get_user_profile(request, user_id):
    try:
        

        # Fetch user details
        user = user_collection.find_one({"_id": ObjectId(user_id)}, {"password": 0})  # Exclude password

        if not user:
            return JsonResponse({"error": "User not found"}, status=404)

        # Fetch addresses for the user
        addresses = list(address_collection.find({"user_id": ObjectId(user_id)}, {"_id": 0, "user_id": 0}))

        # Prepare the response
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

        return JsonResponse(user_data, status=200)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
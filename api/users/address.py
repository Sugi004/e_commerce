from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
import json
from ..mongoDb import get_collection
from bson import ObjectId
from marshmallow import ValidationError
from .userSchema import AddressSchema

user_collection = get_collection("users")
address_collection = get_collection("addresses")

def initialize_address_collection():
    """Initialize address collection with required indexes"""
    address_collection = get_collection("addresses")
    
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

def handle_response(request, success_message, error_message, status=200, redirect_url=None):
    """Helper function to handle both JSON and template responses"""
    is_json_request = request.content_type == "application/json"
    
    if is_json_request:
        if status >= 400:
            return JsonResponse({"error": error_message}, status=status)
        return JsonResponse({"message": success_message}, status=status)
    
    if status >= 400:
        messages.error(request, error_message)
    else:
        messages.success(request, success_message)
    
    return redirect(redirect_url or 'profile')

@csrf_exempt
def add_address(request, user_id):
    if request.method == "POST":
        try:
            is_json_request = request.content_type == "application/json"
            if is_json_request:
                data = json.loads(request.body)
                user_id = data.get("user_id")
                address = data.get("address")
            else:
                user_id = request.POST.get("user_id", "").strip()
                address = request.POST.get("address", "").strip()

            if not user_id or not address:
                return handle_response(
                    request,
                    None,
                    "User ID and address are required",
                    400
                )

            # Validate address using AddressSchema
            schema = AddressSchema()
            validated_address = schema.load(address)

            # Ensure the user exists
            user = user_collection.find_one({"_id": ObjectId(user_id)})
            if not user:
                return handle_response(
                    request,
                    None,
                    "User not found",
                    404
                )
            try:
                address_collection.update_one(
                    {"user_id": ObjectId(user_id)},
                    {
                        "$push": {"addresses": validated_address}
                    },
                    upsert=True
                )
                return handle_response(
                    request,
                    "Address added successfully",
                    None,
                    201
                )
            except Exception as e:
                  if "duplicate key error" in str(e).lower():
                    address_collection.update_one(
                        {
                            "user_id": ObjectId(user_id),
                            "addresses.type": validated_address["type"]
                        },
                        {
                            "$set": {"addresses.$": validated_address}
                        }
                    )
                    return handle_response(
                        request,
                        "Address updated successfully",
                        None,
                        200
                    )
            raise

        except ValidationError as e:
            return handle_response(
                request,
                None,
                e.messages,
                400
            )
        except json.JSONDecodeError:
            return handle_response(
                request,
                None,
                "Invalid JSON",
                400
            )
        except Exception as e:
            return handle_response(
                request,
                None,
                str(e),
                500
            )

    return handle_response(
        request,
        None,
        "Method not allowed",
        405
    )

def get_user_profile(request, user_id):
    try:
        user = user_collection.find_one({"_id": ObjectId(user_id)}, {"password": 0})
        if not user:
            return handle_response(
                request,
                None,
                "User not found",
                404
            )

        addresses = list(address_collection.find(
            {"user_id": ObjectId(user_id)},
            {"_id": 0, "user_id": 0}
        ))

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

        if request.content_type == "application/json":
            return JsonResponse(user_data, status=200)
        
        return render(request, 'profile.html', {'user_data': user_data})

    except Exception as e:
        return handle_response(
            request,
            None,
            str(e),
            500
        )
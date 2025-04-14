from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.sessions.models import Session
from django.utils.crypto import get_random_string
from marshmallow import ValidationError
from .schema import ProductSchema
from api.mongoDb import get_collection
import json
from bson import ObjectId
from types import SimpleNamespace
from datetime import datetime

# Fetch the collection dynamically
product_collection = get_collection("products")
reviews_collection = get_collection("reviews") 
users_collection = get_collection("users")
product_schema = ProductSchema()

def get_products(request):
    if request.method == "GET":
        try:
            # Handle query parameters for filtering/sorting
            query = {}
            category = request.GET.get("category")
            if category:
                query["category"] = category
            
            sort_by = request.GET.get("sort_by", "name") 
            order = 1 if request.GET.get("order", "asc") == "asc" else -1
            
            # Retrieve filtered/sorted products from MongoDB
            products = list(product_collection.find(query).sort(sort_by, order))
            
            # Convert ObjectId to string for JSON serialization
            for product in products:
                product["_id"] = str(product["_id"])  # Convert ObjectId to string
            
            return JsonResponse(products, safe=False, status=200)
        
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid HTTP method"}, status=405)

def get_single_product(request, product_id):
    try:
        # Fetch the product by its ObjectId
        product = product_collection.find_one({"_id": ObjectId(product_id)})

        if product:
            product["id"] = str(product["_id"]) 
         # Fetch approved reviews for the product
            reviews_data = reviews_collection.find_one({"product_id": product_id})
            approved_reviews = []
            if reviews_data and "reviews" in reviews_data:
                
                for review in reviews_data["reviews"]:
                    if review["status"] == "approved":
                        
                        user = users_collection.find_one({"_id": ObjectId(review["user_id"])})
                        username = user["name"] if user and "name" in user else "Unknown User"
                        print(username)
                        approved_reviews.append( {
                                    "username": username,
                                    "rating": review["rating"],
                                    "review": review["review"],
                                    "status": review["status"],
                                    "created_at": review["created_at"],
                                    "updated_at": review["updated_at"],
                                })


            approved_reviews = approved_reviews[:5]  # Limit to 5 reviews
            context = {
                'product': product,
                'reviews': approved_reviews,
            }

            return render(request, 'product_detail.html', context)
        else:
            return JsonResponse({"error": "Product not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)



def create_product(request):
    if request.method == "POST":
        try:
            # Check if the request is from a form submission or an API
            if request.content_type == "application/json":
                # Handle JSON-based API request
                data = json.loads(request.body)
            else:
                # Handle form-based submission
                data = {
                    "name": request.POST.get("name"),
                    "description": request.POST.get("description"),
                    "price": float(request.POST.get("price", 0)),
                    "category": request.POST.get("category"),
                    "tags": request.POST.getlist("tags"),
                    "attributes": {
                        "brand": request.POST.get("brand"),
                        "color": request.POST.get("color"),
                        "model": request.POST.get("model"),
                    },
                    "stock": int(request.POST.get("stock", 0)),
                    "seller_id": request.POST.get("seller_id"),
                }

            # Normalize single item or multiple items
            products = [data] if isinstance(data, dict) else data

            valid_products = []
            for product in products:
                try:
                    validated_product = product_schema.load(product)  # Marshmallow validation
                except ValidationError as err:
                    if request.content_type != "application/json":
                        return render(request, "admin/create_product.html", {"error": err.messages})
                    return JsonResponse({"error": err.messages}, status=400)

                # Check for duplicates
                existing_product = product_collection.find_one({
                    "name": {"$regex": f"^{validated_product['name']}$", "$options": "i"},
                    "attributes.brand": {"$regex": f"^{validated_product['attributes']['brand']}$", "$options": "i"},
                    "attributes.color": {"$regex": f"^{validated_product['attributes']['color']}$", "$options": "i"},
                    "attributes.model": {"$regex": f"^{validated_product['attributes']['model']}$", "$options": "i"},
                })

                if existing_product:
                    error_message = f"Product '{validated_product['name']}' with these attributes already exists"
                    if request.content_type != "application/json":
                        return render(request, "admin/create_product.html", {"error": error_message})
                    return JsonResponse({"error": error_message}, status=400)

                valid_products.append(validated_product)

            if not valid_products:
                error_message = "No valid products to insert"
                if request.content_type != "application/json":
                    return render(request, "admin/create_product.html", {"error": error_message})
                return JsonResponse({"error": error_message}, status=400)

            product_collection.insert_many(valid_products)

            success_message = f"{len(valid_products)} Product(s) created successfully"
            if request.content_type != "application/json":
                return render(request, "admin/create_product.html", {"message": success_message})
            return JsonResponse({"message": success_message}, status=201)

        except json.JSONDecodeError:
            error_message = "Invalid JSON"
            if request.content_type != "application/json":
                return render(request, "admin/create_product.html", {"error": error_message})
            return JsonResponse({"error": error_message}, status=400)
        except Exception as e:
            error_message = str(e)
            if request.content_type != "application/json":
                return render(request, "admin/create_product.html", {"error": error_message})
            return JsonResponse({"error": error_message}, status=500)

    elif request.method == "GET":
        # Render the product creation form for GET requests
        return render(request, "admin/create_product.html")

    return JsonResponse({"error": "Method not allowed"}, status=405)

def delete_product(request, product_id):
    if request.method == "DELETE":
        try:
            if not ObjectId.is_valid(product_id):
                error_message = "Invalid product ID format"
                return JsonResponse({"error": error_message}, status=400)

            product = product_collection.find_one({"_id": ObjectId(product_id)})
            if not product:
                error_message = "Product not found"
                return JsonResponse({"error": error_message}, status=404)

            result = product_collection.delete_one({"_id": ObjectId(product_id)})
            if result.deleted_count == 0:
                error_message = "Failed to delete product"
                return JsonResponse({"error": error_message}, status=500)

            success_message = f"Product with ID {product_id} deleted successfully"
            return JsonResponse({"message": success_message}, status=200)

        except Exception as e:
            error_message = str(e)
            return JsonResponse({"error": error_message}, status=500)

    return JsonResponse({"error": "Method not allowed"}, status=405)

def update_product(request, product_id):
    if request.method in ["PUT", "PATCH"]:
        try:
            if not ObjectId.is_valid(product_id):
                error_message = "Invalid product ID format"
                return JsonResponse({"error": error_message}, status=400)

            product = product_collection.find_one({"_id": ObjectId(product_id)})
            if not product:
                error_message = "Product not found"
                return JsonResponse({"error": error_message}, status=404)

            data = json.loads(request.body)
            try:
                validated_data = product_schema.load(data, partial=True)
            except ValidationError as err:
                return JsonResponse({"error": err.messages}, status=400)

            update_result = product_collection.update_one(
                {"_id": ObjectId(product_id)},
                {"$set": validated_data}
            )

            if update_result.matched_count == 0:
                error_message = "No matching product found to update"
                return JsonResponse({"error": error_message}, status=500)

            success_message = f"Product with ID {product_id} updated successfully"
            return JsonResponse({"message": success_message}, status=200)

        except json.JSONDecodeError:
            error_message = "Invalid JSON format"
            return JsonResponse({"error": error_message}, status=400)
        except Exception as e:
            error_message = str(e)
            return JsonResponse({"error": error_message}, status=500)

    return JsonResponse({"error": "Method not allowed"}, status=405)

def submit_review(request, product_id):
    """Allow customers to submit reviews for a product."""
    if request.method == "POST":
        try:
            print(request.user_data)
            # Check if the product exists
            product = product_collection.find_one({"_id": ObjectId(product_id)})
            if not product:
                error_message = "Product not found"
                if request.content_type != "application/json":
                    messages.error(request, error_message)
                    return redirect("get_single_product", product_id=product_id)
                return JsonResponse({"error": error_message}, status=404)

            # Determine the user_id
            if request.user_data and request.user_data.get("user_id"):
                user_id = request.user_data.get("user_id")
            else:
                # Generate or retrieve a unique session ID for the guest user
                if not request.session.session_key:
                    request.session.create() 
                user_id = request.session.session_key

            # Extract review data from the request
            if request.content_type == "application/json":
                data = json.loads(request.body)
            else:
                data = {
                    "rating": int(request.POST.get("rating", 0)),
                    "review": request.POST.get("review"),
                }

            # Validate the review data
            if not data.get("rating") or not data.get("review"):
                error_message = "All fields (rating, review) are required."
                if request.content_type != "application/json":
                    messages.error(request, error_message)
                    return redirect("get_single_product", product_id=product_id)
                return JsonResponse({"error": error_message}, status=400)

            if data["rating"] < 1 or data["rating"] > 5:
                error_message = "Rating must be between 1 and 5."
                if request.content_type != "application/json":
                    messages.error(request, error_message)
                    return redirect("get_single_product", product_id=product_id)
                return JsonResponse({"error": error_message}, status=400)

            review = {
                "id": ObjectId(),
                "user_id": user_id,
                "rating": data["rating"],
                "status": "pending", 
                "review": data["review"],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }

            existing_reviews = reviews_collection.find_one({"product_id": product_id})

            if existing_reviews:
                # Append the new review to the existing reviews list
                reviews_collection.update_one(
                    {"product_id": product_id},
                    {"$push": {"reviews": review}}
                )
            else:
                # Create a new document for the product with the review
                reviews_collection.insert_one({
                    "product_id": product_id,
                    "reviews": [review]
                })

            success_message = "Review submitted successfully and is pending moderation."
            if request.content_type != "application/json":
                messages.success(request, success_message)
                return redirect("get_single_product", product_id=product_id)
            return JsonResponse({"message": success_message}, status=201)

        except json.JSONDecodeError:
            error_message = "Invalid JSON format"
            if request.content_type != "application/json":
                messages.error(request, error_message)
                return redirect("get_single_product", product_id=product_id)
            return JsonResponse({"error": error_message}, status=400)
        except Exception as e:
            error_message = str(e)
            if request.content_type != "application/json":
                messages.error(request, error_message)
                return redirect("get_single_product", product_id=product_id)
            return JsonResponse({"error": error_message}, status=500)

    error_message = "Method not allowed"
    if request.content_type != "application/json":
        messages.error(request, error_message)
        return redirect("get_single_product", product_id=product_id)
    return JsonResponse({"error": error_message}, status=405)

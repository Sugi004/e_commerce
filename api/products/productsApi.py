from ..modules import *
from .schema import ProductSchema, IndividualReviewSchema
from ..utils.date_utils import validate_and_convert_dates


# Fetch the schema
product_schema = ProductSchema()
review_schema = IndividualReviewSchema()

# @csrf_exempt
# def get_products(request):
#     """Fetch products with optional filtering and sorting."""
#     if request.method == "GET":
#         try:
#             # Handle query parameters for filtering/sorting
#             query = {}
#             category = request.GET.get("category")
#             if category:
#                 query["category"] = category

#             query["is_active"] = True # Only fetch active products

#             sort_by = request.GET.get("sort_by", "name")
#             order = 1 if request.GET.get("order", "asc") == "asc" else -1

#             # Retrieve filtered/sorted products from MongoDB
#             products = list(products_collection.find(query).sort(sort_by, order))

#             # Convert ObjectId to string for template usage
#             for product in products:
#                 product["_id"] = str(product["_id"])

#             # Add a success message
#             messages.success(request, f"{len(products)} products fetched successfully.")
#             return redirect("render_products")  # Redirect to the products page

#         except Exception as e:
#             # Add an error message
#             messages.error(request, f"Error fetching products: {str(e)}")
#             return redirect("render_products")  # Redirect to the products page

#     # Add an error message for invalid HTTP methods
#     messages.error(request, "Invalid HTTP method.")
#     return redirect("render_products")

@csrf_exempt
def get_single_product(request, id):
    try:
        # Fetch the product by its ObjectId
        product = products_collection.find_one({"_id": ObjectId(id)})

        if product:
            product["id"] = str(product["_id"]) 


            return render(request, 'products/product_detail.html', {"product": product})
        else:
            messages.error(request, "Product not found")
            return redirect('render_products')
    except Exception as e:
        messages.error(request, f"Error fetching product: {str(e)}")
        return redirect('render_products')

@csrf_exempt
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
                    "is_active": request.POST.get("is_active") == "on",  # Convert checkbox to boolean
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
                        messages.error(request, f"Validation error: {err.messages}")
                        return render(request, "products/create_product.html")
                    return JsonResponse({"error": err.messages}, status=400)

                # Check for duplicates
                existing_product = products_collection.find_one({
                    "name": {"$regex": f"^{validated_product['name']}$", "$options": "i"},
                    "attributes.brand": {"$regex": f"^{validated_product['attributes']['brand']}$", "$options": "i"},
                    "attributes.color": {"$regex": f"^{validated_product['attributes']['color']}$", "$options": "i"},
                    "attributes.model": {"$regex": f"^{validated_product['attributes']['model']}$", "$options": "i"},
                })

                if existing_product:
                    error_message = f"Product '{validated_product['name']}' with these attributes already exists"
                    if request.content_type != "application/json":
                        messages.error(error_message)
                        return render(request, "products/create_product.html")
                    return JsonResponse({"error": error_message}, status=400)

                valid_products.append(validated_product)

            if not valid_products:
                error_message = "No valid products to insert"
                if request.content_type != "application/json":
                    messages.error(error_message)
                    return render(request, "products/create_product.html")
                return JsonResponse({"error": error_message}, status=400)

            products_collection.insert_many(valid_products)

            success_message = f"{len(valid_products)} Product(s) created successfully"
            if request.content_type != "application/json":
                messages.success(success_message)
                return render(request, "products/create_product.html")
            return JsonResponse({"message": success_message}, status=201)

        except json.JSONDecodeError:
            error_message = "Invalid JSON"
            if request.content_type != "application/json":
                messages.error(error_message)
                return render(request, "products/create_product.html")
            return JsonResponse({"error": error_message}, status=400)
        except Exception as e:
            error_message = str(e)
            if request.content_type != "application/json":
                messages.error(request, f"Error creating product: {error_message}")
                return render(request, "products/create_product.html")
            return JsonResponse({"error": error_message}, status=500)

    elif request.method == "GET":
        # Render the product creation form for GET requests
        return render(request, "products/create_product.html")

    return JsonResponse({"error": "Method not allowed"}, status=405)

@csrf_exempt
def delete_product(request, product_id):
    if request.method == 'POST' and request.POST.get('_method') == 'DELETE':
        try:
            if not ObjectId.is_valid(product_id):
                messages.error(request, "Invalid product ID format")
                return redirect('manage_products')

            # Find the product by ID
            product = products_collection.find_one({"_id": ObjectId(product_id)})

            if not product:
                messages.error(request, "Product not found")
                return redirect('manage_products')
            # Delete the product
            result = products_collection.delete_one({"_id": ObjectId(product_id)})

            if result.deleted_count == 0:
                messages.error(request, "Failed to delete product")
                return redirect('manage_products')

            messages.success(request, f"Product {product['name']} deleted successfully")
            return redirect('manage_products')

        except Exception as e:
            messages.error(request, f"Error deleting product: {str(e)}")
            return redirect('manage_products')

    messages.error(request, "Method not allowed")
    return redirect('manage_products')

@csrf_exempt
def update_product(request, product_id):
    if request.method in ["POST"]:  # Use POST for form-based updates
        try:
            if not ObjectId.is_valid(product_id):
                messages.error(request, "Invalid product ID format")
                return redirect('manage_products')

            product = products_collection.find_one({"_id": ObjectId(product_id)})
            if not product:
                messages.error(request, "Product not found")
                return redirect('render_products')

            # For form-based update
            data = {
                "name": request.POST.get("name", product.get("name")),
                "description": request.POST.get("description", product.get("description")),
                "price": float(request.POST.get("price", product.get("price", 0))),
                "category": request.POST.get("category", product.get("category")),
                "tags": request.POST.getlist("tags") or product.get("tags", []),
                "is_active": request.POST.get("is_active") == "on" if "is_active" in request.POST else product.get("is_active", True),
                "attributes": {
                    "brand": request.POST.get("brand", product.get("attributes", {}).get("brand")),
                    "color": request.POST.get("color", product.get("attributes", {}).get("color")),
                    "model": request.POST.get("model", product.get("attributes", {}).get("model")),
                },
                "stock": int(request.POST.get("stock", product.get("stock", 0))),
                "seller_id": request.POST.get("seller_id", product.get("seller_id")),
            }

            try:
                validated_data = product_schema.load(data, partial=True)
            except ValidationError as err:
                messages.error(request, f"Validation error: {err.messages}")
                return redirect('manage_products')

            update_result = products_collection.update_one(
                {"_id": ObjectId(product_id)},
                {"$set": validated_data}
            )

            if update_result.matched_count == 0:
                messages.error(request, "No matching product found to update")
                return redirect('manage_products')

            messages.success(request, f"Product {data['name']} updated successfully")
            return redirect('manage_products')

        except Exception as e:
            messages.error(request, f"Error updating product: {str(e)}")
            return redirect('manage_products')

    messages.error(request, "Method not allowed")
    return redirect('render_products')

@csrf_exempt
def submit_review(request, product_id):
    """Allow customers to submit reviews for a product."""
    if request.method == "POST":
        try:
            # Check if the product exists
            product = products_collection.find_one({"_id": ObjectId(product_id)})
            if not product:
                messages.error(request, "Product not found")
                return redirect("get_single_product", id=product_id)

            # Extract review data from the request
            data = {
                "rating": int(request.POST.get("rating", 0)),
                "review": request.POST.get("review"),
            }

            # Validate the review data
            if not data.get("rating") or not data.get("review"):
                messages.error(request, "All fields (rating, review) are required.")
                return redirect("get_single_product", id=product_id)

            if data["rating"] < 1 or data["rating"] > 5:
                messages.error(request, "Rating must be between 1 and 5.")
                return redirect("get_single_product", id=product_id)

            review = {
                "id": ObjectId(),
                "user_id": request.session.session_key,
                "rating": data["rating"],
                "status": "pending",
                "review": data["review"],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }

            review = validate_and_convert_dates(review, ["created_at", "updated_at"])  # Convert dates to ISO format

            # Validate the review data with ReviewSchema
            try:
                validated_review = review_schema.load(review)  # Validate the review data
            except ValidationError as e:
                messages.error(request, f"Review validation failed: {e.messages}")
                return redirect("get_single_product", id=product_id)
            
            # Append the review to the product's reviews
            reviews_collection.update_one(
                {"product_id": product_id},
                {"$push": {"reviews": validated_review}},
                upsert=True
            )

            messages.success(request, "Review submitted successfully and is pending moderation.")
            return redirect("get_single_product", id=product_id)

        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return redirect("get_single_product", id=product_id)

    messages.error(request, "Method not allowed")
    return redirect("get_single_product", id=product_id)
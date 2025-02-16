from django.http import JsonResponse
from django.shortcuts import render
from marshmallow import ValidationError
from .schema import ProductSchema
from api.mongoDb import get_collection
import json
from bson import ObjectId
from types import SimpleNamespace

# Fetch the collection dynamically
product_collection = get_collection("products")
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

def get_single_product(request, id):
    try:
        # Fetch the product by its ObjectId
        product = product_collection.find_one({"_id": ObjectId(id)})

        if product:
            product["_id"] = str(product["_id"]) 
            product_obj = SimpleNamespace(**product)
        
            context = {
                'product': product_obj,
                'product_id': product_obj._id
            }

            print(product_obj._id)
            return render(request, 'productDetail.html', context)
        else:
            return JsonResponse({"error": "Product not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)



def create_product(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)

            # Normalize single item or multiple items
            products = [data] if isinstance(data, dict) else data

            product_collection = get_collection("products")

            valid_products = []
            for product in products:
                try:
                    validated_product = product_schema.load(product)  # Marshmallow validation
                except ValidationError as err:
                    return JsonResponse({"error": err.messages}, status=400)

                # Check for duplicates
                existing_product = product_collection.find_one({
                    "name": {"$regex": f"^{validated_product['name']}$", "$options": "i"},
                    "attributes.brand": {"$regex": f"^{validated_product['attributes']['brand']}$", "$options": "i"},
                    "attributes.color": {"$regex": f"^{validated_product['attributes']['color']}$", "$options": "i"},
                    "attributes.model": {"$regex": f"^{validated_product['attributes']['model']}$", "$options": "i"},
                })

                if existing_product:
                    return JsonResponse(
                        {"error": f"Product '{validated_product['name']}' with these attributes already exists"},
                        status=400
                    )

                valid_products.append(validated_product)

            if not valid_products:
                return JsonResponse({"error": "No valid products to insert"}, status=400)

            product_collection.insert_many(valid_products)
            return JsonResponse({"message": f"{len(valid_products)} Product(s) created successfully"}, status=201)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Method not allowed"}, status=405)

def delete_product(request, product_id):
    if request.method == "DELETE":
        try:
            if not ObjectId.is_valid(product_id):
                return JsonResponse({"error": "Invalid product ID format"}, status=400)
            product_collection = get_collection("products")

            # Find the product by ID
            product = product_collection.find_one({"_id": ObjectId(product_id)})
            print(product)

            if not product:
                return JsonResponse({"error": "Product not found"}, status=404)

            # Delete the product
            result = product_collection.delete_one({"_id": ObjectId(product_id)})

            if result.deleted_count == 0:
                return JsonResponse({"error": "Failed to delete product"}, status=500)

            return JsonResponse({"message": f"Product with ID {product_id} deleted successfully"}, status=200)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Method not allowed"}, status=405)

def update_product(request, product_id):
    if request.method in ["PUT", "PATCH"]:
        try:
            if not ObjectId.is_valid(product_id):
                return JsonResponse({"error": "Invalid product ID format"}, status=400)

            product_collection = get_collection("products")

            product = product_collection.find_one({"_id": ObjectId(product_id)})
            if not product:
                return JsonResponse({"error": "Product not found"}, status=404)

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
                return JsonResponse({"error": "No matching product found to update"}, status=500)

            return JsonResponse({"message": f"Product with ID {product_id} updated successfully"}, status=200)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Method not allowed"}, status=405)

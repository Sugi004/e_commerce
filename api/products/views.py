# from django.http import JsonResponse
# from .schema import ProductSchema
# from .productsApi import get_products
# from django.shortcuts import render
# import json

# # Initialize schema
# product_schema = ProductSchema()


# def render_products(request):
#     try:
        
#         # Call the get_products function directly
#         response = get_products(request)

#         # If the response is JsonResponse, extract JSON data
#         if isinstance(response, JsonResponse):
#             products = response.content.decode('utf-8')  # Decode JSON response
#             products = json.loads(products)  # Convert JSON string to Python dict
            
#         else:
#             products = []

#         # Render the template with product data
#         return render(request, "viewProducts.html", {"products": products})

#     except Exception as e:
#         return render(request, "error.html", {"error": str(e)})


import logging
import json
from django.http import JsonResponse
from django.shortcuts import render
from .productsApi import get_products  # Adjust import based on where your get_products function is defined

# Set up logging
logger = logging.getLogger(__name__)

def render_products(request):
    try:
        # Assuming get_products() fetches the product list correctly
        response = get_products(request)

        if isinstance(response, JsonResponse):
            # Decode the JSON response content
            products = json.loads(response.content.decode('utf-8'))
        else:
            products = []  # Handle other cases where response isn't a JsonResponse

        # Now you can safely assign _id as a string to a new attribute
        for product in products:
            product['product_id'] = str(product.get('_id', ''))  # Assign a string version of _id to a new attribute

        # Render the template with the modified products list
        return render(request, "viewProducts.html", {"products": products})

    except Exception as e:
        logger.error(str(e), exc_info=True)
        return render(request, "error.html", {"error": str(e)})
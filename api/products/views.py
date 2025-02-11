
import logging
import json
from django.http import JsonResponse
from django.shortcuts import render
from .productsApi import get_products, product_collection  # Adjust import based on where your get_products function is defined

# Set up logging
logger = logging.getLogger(__name__)



def render_products(request):
    try:
        # Get products with category filtering
        response = get_products(request)  # This will automatically handle category parameter

        if isinstance(response, JsonResponse):
            # Decode the JSON response content
            products = json.loads(response.content.decode('utf-8'))
        else:
            products = []

        # Get categories for the dropdown menu
        categories = list(product_collection.distinct("category"))

        # Process products for template
        for product in products:
            product['product_id'] = str(product.get('_id', ''))

        context = {
            "products": products,
            "categories": categories,
            "selected_category": request.GET.get("category")
        }

        return render(request, "viewProducts.html", context)

    except Exception as e:
        logger.error(str(e), exc_info=True)
        return render(request, "error.html", {"error": str(e)})
import logging
import json
from django.http import JsonResponse
from django.shortcuts import render
from .productsApi import get_products, product_collection
from django.core.paginator import Paginator 
from ..cart_management.cart_management_db import get_user_cart, get_cart_items

# Set up logging
logger = logging.getLogger(__name__)



def render_products(request):
    try:
        # Get products with category filtering
        response = get_products(request)

        if isinstance(response, JsonResponse):
            # Decode the JSON response content
            products = json.loads(response.content.decode('utf-8'))
        else:
            products = []

        # Get categories for the dropdown menu
        categories = list(product_collection.distinct("category"))

        # Process products for template
        for product in products:
            product['id'] = str(product.get('_id', ''))

        try:
            page_number = int(request.GET.get('page', 1))
        except ValueError:
            page_number = 1

        paginator = Paginator(products, 28)

        try:
            page_obj = paginator.page(page_number)
        except:
            page_obj = paginator.page(1)

        cart_count = 0
        if request.user_data:
            cart = get_user_cart(user_id=request.user_data["_id"])
        else:
            cart = get_user_cart(session_id=request.session.session_key)
            
        if cart:
            cart_items = get_cart_items(cart["_id"])

           
            cart_count = len(cart_items)


        context = {
            "products": page_obj,
            "categories": categories,
            "selected_category": request.GET.get("category"),
            "page_obj": page_obj,
            "is_paginated": paginator.num_pages > 1,
            "total_products": len(products),
            "showing_start": (page_number - 1) * 28 + 1,
            "showing_end": min(page_number * 28, len(products)),
            "cart_count": cart_count,
        }

        return render(request, "viewProducts.html", context)

    except Exception as e:
        logger.error(f"Error in render_products: {str(e)}", exc_info=True)
        return render(request, "error.html", {"error": str(e)})
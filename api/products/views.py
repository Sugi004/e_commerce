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
        cart = None

        # Debug logging
        logger.debug(f"User data: {getattr(request, 'user_data', None)}")
        logger.debug(f"Session key: {request.session.session_key}")

        # Handle authenticated user
        if hasattr(request, 'user_data') and request.user_data:
            user_id = request.user_data.get('user_id')  # Changed from '_id' to 'user_id'
            logger.debug(f"Authenticated user_id: {user_id}")
            if user_id:
                cart = get_user_cart(user_id=str(user_id))  # Ensure user_id is string
                logger.debug(f"Authenticated user cart: {cart}")
        
        # Handle guest user
        if not cart:
            if not request.session.session_key:
                request.session.create()
                request.session.save()  # Ensure session is saved
            logger.debug(f"Guest session key: {request.session.session_key}")
            cart = get_user_cart(session_id=request.session.session_key)
            logger.debug(f"Guest cart: {cart}")

        # Calculate cart count
        if cart:
            cart_items = get_cart_items(cart["_id"])
            cart_count = len(cart_items)
            logger.debug(f"Cart count: {cart_count}")

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
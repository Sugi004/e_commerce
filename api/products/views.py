from ..modules import render, products_collection
from django.core.paginator import Paginator 
from ..cart_management.cart_management_db import get_user_cart, get_cart_items



def render_products(request):
    try:
        # Get the search query from the request
        query = request.GET.get("query", "").strip()
        selected_category = request.GET.get("category", "").strip()

         # Build the base filter
        filter_query = {"is_active": True}

        # Add search filter
        if query:
            filter_query["$or"] = [
                {"name": {"$regex": query, "$options": "i"}},
                {"category": {"$regex": query, "$options": "i"}},
                {"brand": {"$regex": query, "$options": "i"}}
            ]

        # Add category filter
        if selected_category:
            filter_query["category"] = selected_category

        # Fetch products from the database  
        products = list(products_collection.find(filter_query))

        # Get categories for the dropdown menu
        categories = list(products_collection.distinct("category"))

        # Process products for template
        for product in products:
            product['id'] = str(product.get('_id', ''))

        # Handle pagination
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

        # Handle authenticated user
        if hasattr(request, 'user_data') and request.user_data:
            user_id = request.user_data.get('user_id')  

            if user_id:
                cart = get_user_cart(user_id=str(user_id))  # Ensure user_id is string
        
        # Handle guest user
        if not cart:
            if not request.session.session_key:
                request.session.create()
                request.session.save()  # Ensure session is saved
            cart = get_user_cart(session_id=request.session.session_key)

        # Calculate cart count
        if cart:
            cart_items = get_cart_items(cart["_id"])
            cart_count = len(cart_items)

        # Prepare context for rendering
        context = {
            "products": page_obj,
            "categories": categories,
            "selected_category": selected_category,
            "page_obj": page_obj,
            "is_paginated": paginator.num_pages > 1,
            "total_products": len(products),
            "showing_start": (page_number - 1) * 28 + 1,
            "showing_end": min(page_number * 28, len(products)),
            "cart_count": cart_count,
            "query": query
        }

        return render(request, "products/view_products.html", context)

    except Exception as e:
        print(f"Error in render_products: {str(e)}")
        return render(request, "error.html", {"error": str(e)})
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from .cart_management_db import (
    get_user_cart,
    create_cart,
    update_cart_item,
    get_cart_items,
    clear_cart
)
from bson import ObjectId, errors
import json
from datetime import datetime
from ..mongoDb import get_collection

product_collection = get_collection("products")

def handle_response(request, success_message, error_message, status=200, redirect_url=None):
    """Helper function to handle JSON responses and messages"""
    is_json_request = request.content_type == "application/json"
    
    if is_json_request:
        response_data = {
            "status": status,
            "redirect_url": redirect_url
        }
        if status >= 400:
            response_data["error"] = error_message
        else:
            response_data["message"] = success_message
        return JsonResponse(response_data, status=status)
    
    # Add message to session if provided
    if status >= 400 and error_message:
        messages.error(request, error_message)
    elif success_message:
        messages.success(request, success_message)
    
    # Return JsonResponse for success/error messages
    return JsonResponse({
        "status": status,
        "message": success_message if status < 400 else error_message
    })

@csrf_exempt
def view_cart(request):
    """View cart contents"""
    try:
        # Get cart based on user authentication
        if request.user_data:
            cart = get_user_cart(user_id=request.user_data["_id"])
        else:
            cart = get_user_cart(session_id=request.session.session_key)

        if not cart:
            return render(request, 'cart.html', {
                "cart_items": [], 
                "cart_total": 0,
                "cart_count": 0
            })

        # Get cart items with product details
        cart_items = get_cart_items(cart["_id"])
        
        # Calculate totals and apply discounts
        cart_total = 0
        cart_count = 0
        
        for item in cart_items:

            product = item["product"]
            quantity = item["quantity"]
            price = float(product.get("price", 0))
            
             # Convert _id to id for template access
            item['product']['id'] = str(item['product']['_id'])
            
            # Apply discount if available
            if product.get("discount"):
                discount = float(product["discount"]) / 100
                price = price * (1 - discount)
                
            item["subtotal"] = price * quantity
            cart_total += item["subtotal"]
            cart_count = len(cart_items)
            
        context = {
            "cart_items": cart_items,  
            "cart_total": round(cart_total, 2),
            "cart_count": cart_count, 
        }
        response = render(request, 'cart.html', context)
        
        if request.content_type == "application/json":
            return JsonResponse(context)
        
        return response
        

    except Exception as e:
        print(f"Error viewing cart: {str(e)}")  # Debug print
        return handle_response(request, None, str(e), 500)

@csrf_exempt
def add_to_cart(request, product_id):
    """Add item to cart"""
    if request.method != "POST":
        return handle_response(request, None, "Method not allowed", 405)

    try:
        # 1. Validate product ID
        try:
            product_object_id = ObjectId(product_id)
        except errors.InvalidId:
            return handle_response(request, None, "Invalid product ID", 400)

        # 2. Validate product exists and check stock
        product = product_collection.find_one({"_id": product_object_id})
        if not product:
            return handle_response(request, None, "Product not found", 404)
        
        if product.get('stock', 0) <= 0:
            return handle_response(request, None, "Product out of stock", 400)

        # 3. Get or create cart with error handling
        try:
            if request.user_data:
                cart = get_user_cart(user_id=request.user_data["_id"])
                if not cart:
                    cart_id = create_cart(user_id=request.user_data["_id"])
                    cart = get_user_cart(user_id=request.user_data["_id"])
                    if not cart:
                        raise Exception("Failed to create cart")
            else:
                # Handle guest cart
                if not request.session.session_key:
                    request.session.create()
                cart = get_user_cart(session_id=request.session.session_key)
                if not cart:
                    cart_id = create_cart(session_id=request.session.session_key)
                    cart = get_user_cart(session_id=request.session.session_key)
                    if not cart:
                        raise Exception("Failed to create guest cart")
        except Exception as e:
            return handle_response(request, None, f"Cart creation failed: {str(e)}", 500)

        # 4. Parse and validate quantity
        try:
            quantity = 1
            if request.content_type == "application/json":
                data = json.loads(request.body)
                quantity = int(data.get("quantity", 1))
            else:
                # Handle form data
                form_quantity = request.POST.get("quantity")
                if form_quantity:
                    quantity = int(form_quantity)

            # Validate quantity value
            if quantity <= 0:
                return handle_response(request, None, "Quantity must be positive", 400)
            
            if quantity > product.get('stock', 0):
                return handle_response(
                    request, 
                    None, 
                    f"Only {product.get('stock')} items available", 
                    400
                )

        except (json.JSONDecodeError, ValueError):
            return handle_response(request, None, "Invalid quantity format", 400)

        # 5. Check existing cart item and update total quantity
        current_cart_items = get_cart_items(cart["_id"])
        existing_item = next(
            (item for item in current_cart_items 
             if str(item["product"]["_id"]) == product_id), 
            None
        )

        if existing_item:
            new_quantity = existing_item["quantity"] + quantity
            if new_quantity > product.get('stock', 0):
                return handle_response(
                    request, 
                    None, 
                    f"Cannot add {quantity} more items. Only {product.get('stock') - existing_item['quantity']} available", 
                    400
                )

        # 6. Update cart with error handling
        try:
            update_cart_item(str(cart["_id"]), str(product_id), quantity)
        except Exception as e:
            return handle_response(request, None, f"Failed to update cart: {str(e)}", 500)

        # 7. Return success response
        if request.content_type == "application/json":
            return JsonResponse({
                "message": "Item added to cart successfully",
                "cart_count": quantity,
            }, status=200)
        
        messages.success(request, "Item added to cart successfully")
        return redirect("view_cart")

    except Exception as e:
        return handle_response(request, None, str(e), 500)

@csrf_exempt
def update_cart(request, product_id):
    """Update cart item quantity"""
    if request.method != "POST":
        return handle_response(request, None, "Method not allowed", 405)

    try:
        # Get cart
        if request.user_data:
            cart = get_user_cart(user_id=request.user_data["_id"])
        else:
            cart = get_user_cart(session_id=request.session.session_key)

        if not cart:
            return handle_response(request, None, "Cart not found", 404)

        # Get action from request
        action = request.POST.get("action")
        if request.content_type == "application/json":
            data = json.loads(request.body)
            action = data.get("action")

        if action not in ["increase", "decrease", "remove"]:
            return handle_response(request, None, "Invalid action", 400)

        # Get current quantity
        cart_items = get_cart_items(cart["_id"])
        current_item = next((item for item in cart_items 
                           if str(item["product"]["_id"]) == product_id), None)
        
        if not current_item:
            return handle_response(request, None, "Item not found in cart", 404)

        # Check stock before increasing
        if action == "increase":
            # Check stock before increasing
            product = product_collection.find_one({"_id": ObjectId(product_id)})
            if current_item["quantity"] >= product.get("stock", 0):
                return handle_response(request, None, "Not enough stock available", 400)
            new_quantity = current_item["quantity"] + 1
            message = "Quantity increased"
        else:  # decrease
            new_quantity = max(1, current_item["quantity"] - 1)
            message = "Quantity decreased"
        
         # Update cart with new quantity
        update_cart_item(str(cart["_id"]), str(product_id), new_quantity)
        messages.success(request, message)

        # Get updated cart data
        updated_cart_items = get_cart_items(cart["_id"])
        cart_total = sum(item["subtotal"] for item in updated_cart_items)
        cart_count = sum(item["quantity"] for item in updated_cart_items)

        


        response = redirect("view_cart")

        if request.content_type == "application/json":
            return JsonResponse({
                "status": 200,
                "message": message,
                "cart_total": round(cart_total, 2),
                "cart_count": cart_count
            })

        # Render the cart view with updated data
        return response

    except Exception as e:
        return handle_response(request, None, str(e), 500)

@csrf_exempt
def clear_cart_view(request):
    """Clear all items from cart"""
    if request.method != "POST":
        return handle_response(request, None, "Method not allowed", 405)

    try:
        # Get cart
        if request.user_data:
            cart = get_user_cart(user_id=request.user_data["_id"])
        else:
            cart = get_user_cart(session_id=request.session.session_key)

        if not cart:
            return handle_response(request, None, "Cart not found", 404)

        clear_cart(cart["_id"])
        messages.success(request, "Cart cleared successfully")
        if request.content_type == "application/json":
            return JsonResponse({"message": "Cart cleared successfully"}, status=200)
        
        return render(request, 'cart.html')

    except Exception as e:
        return handle_response(request, None, str(e), 500)

    
@csrf_exempt
def remove_from_cart(request, product_id):
    """Remove specific item from cart"""
    if request.method != "POST":
        return handle_response(request, None, "Method not allowed", 405)

    try:
        # Get cart
        if request.user_data:
            cart = get_user_cart(user_id=request.user_data["_id"])
        else:
            cart = get_user_cart(session_id=request.session.session_key)

        if not cart:
            return handle_response(request, None, "Cart not found", 404)

        # Convert product_id to string for comparison
        product_id_str = str(product_id)

        # Verify item exists in cart
        cart_items = get_cart_items(cart["_id"])
        item_exists = any(str(item["product"]["_id"]) == product_id_str for item in cart_items)
        
        if not item_exists:
            return handle_response(request, None, "Item not found in cart", 404)

        # Remove the specific item
        update_cart_item(str(cart["_id"]), product_id_str, 0, "remove")
        
        # Add success message
        messages.success(request, "Item removed from cart successfully")

        if request.content_type == "application/json":
            # Get updated cart data
            updated_cart_items = get_cart_items(cart["_id"])
            cart_total = sum(item.get("subtotal", 0) for item in updated_cart_items)
            cart_count = sum(item.get("quantity", 0) for item in updated_cart_items)
            
            return JsonResponse({
                "status": 200,
                "message": "Item removed from cart successfully",
                "cart_total": round(cart_total, 2),
                "cart_count": cart_count
            })

        # Redirect to cart page for regular requests
        return redirect('view_cart')

    except Exception as e:
        print(f"Error removing item from cart: {str(e)}")  # Debug print
        return handle_response(request, None, str(e), 500)
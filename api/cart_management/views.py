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
from django.core.mail import send_mail
from decouple import config
from bson import ObjectId, errors
import json
from datetime import datetime, timedelta
from ..mongoDb import get_collection

product_collection = get_collection("products")
carts_collection = get_collection("carts")
user_collection = get_collection("users")

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
            cart = get_user_cart(user_id=request.user_data["user_id"])
        else:
            cart = get_user_cart(session_id=request.session.session_key)

        if not cart:
            return render(request, 'order_management/cart.html', {
                "cart_items": [], 
                "cart_total": 0,
                "cart_count": 0,
                "discount_amount":0,
                "total_with_discount": 0,
                "remaining_for_free_shipping": 50,
            })

        if not request.user_data:
            if cart.get("expires_at"):
                expires_at = cart["expires_at"]
                current_time = datetime.utcnow()
                
                if current_time >= expires_at:
                    # Cart has expired
                    clear_cart(cart["_id"])
                    messages.warning(request, "Your cart has expired. Items have been cleared.")
                    return render(request, 'order_management/cart.html', {
                        "cart_items": [],
                        "cart_total": 0,
                        "cart_count": 0,
                        "discount_amount":0,
                        "total_with_discount": 0,
                        "remaining_for_free_shipping": 50,

                    })
                else:
                    # Calculate time remaining
                    time_remaining = expires_at - current_time
                    hours_remaining = time_remaining.total_seconds() / 3600
                    
                    if hours_remaining < 4:  # Warning when less than 4 hours left
                        messages.warning(
                            request,
                            f"Your cart will expire in {int(hours_remaining)} hours. Please sign up or log in to keep your items."
                        )
                    else:
                        # Always show the initial message for guest carts
                        messages.warning(
                            request,
                            "Guest carts expire after 24 hours. Please sign up or log in to keep your items permanently."
                        )
        # Get cart items with product details
        cart_items = get_cart_items(cart["_id"])
        
        # Calculate totals and apply discounts
        cart_total = 0
        cart_count = 0
        discount = 0
        total_with_discount = 0
        
        for item in cart_items:

            product = item["product"]
            quantity = item["quantity"]
            price = float(product.get("price", 0))
            
             # Convert _id to id for template access
            item['product']['id'] = str(item['product']['_id'])
            
            # Apply discount if available
            if product.get("discount"):
                product_discount = float(product["discount"]) / 100
                price = price * (1 - product_discount)
                
            item["subtotal"] = price * quantity
            cart_total += item["subtotal"]
            cart_count = len(cart_items)
        
        if cart_total > 100:
            discount = cart_total * 0.1  # 10% discount for orders over $100
            total_with_discount = cart_total - discount
        
        free_shipping = 50
        remaining_amount = max(0, free_shipping - cart_total) # Remaining amount eligible for free shipping 

        context = {
            "cart_items": cart_items,  
            "cart_total": round(cart_total, 2),
            "cart_count": cart_count, 
            "discount_amount": round(discount, 2),
            "total_with_discount": round(total_with_discount, 2),
            "remaining_for_free_shipping": round(remaining_amount, 2),
        }
        response = render(request, 'order_management/cart.html', context)
        
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
            if hasattr(request, 'user_data') and request.user_data:
                user_id = request.user_data.get('user_id')
                if not user_id:
                    return handle_response(request, None, "Invalid user data", 400)
                
                cart = get_user_cart(user_id=user_id)
                if not cart:
                    cart_id = create_cart(user_id=user_id)
                    cart = get_user_cart(user_id=user_id)
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
        
        return redirect("view_cart")

    except Exception as e:
        return handle_response(request, None, str(e), 500)

@csrf_exempt
def update_cart(request, product_id):
  
    print(product_id)  # Debug print to check the request data
    if request.method != "POST":
        return handle_response(request, None, "Method not allowed", 405)

    try:
        # Get cart
        if request.user_data:
            cart = get_user_cart(user_id=request.user_data["user_id"])
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
            print(product)
            if current_item["quantity"] >= product.get("stock", 0):
                return handle_response(request, None, "Not enough stock available", 400)
            new_quantity = current_item["quantity"] + 1

            
            
        else:  # decrease
            new_quantity = max(1, current_item["quantity"] - 1)
            
        
         # Update cart with new quantity
        update_cart_item(str(cart["_id"]), str(product_id), new_quantity)

        # Get updated cart data
        updated_cart_items = get_cart_items(cart["_id"])
        cart_total = sum(item["subtotal"] for item in updated_cart_items)
        cart_count = sum(item["quantity"] for item in updated_cart_items)

        response = redirect("view_cart")

        if request.content_type == "application/json":
            return JsonResponse({
                "status": 200,
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
            cart = get_user_cart(user_id=request.user_data["user_id"])
        else:
            cart = get_user_cart(session_id=request.session.session_key)

        if not cart:
            return handle_response(request, None, "Cart not found", 404)

        clear_cart(cart["_id"])
        messages.success(request, "Cart cleared successfully")
        if request.content_type == "application/json":
            return JsonResponse({"message": "Cart cleared successfully"}, status=200)
        
        return render(request, 'order_management/cart.html')

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
            cart = get_user_cart(user_id=request.user_data["user_id"])
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


def send_cart_reminder_emails():
    try:
        
        # Find carts inactive for 24 hours
        inactive_carts = carts_collection.find({
            "updated_at": {"$lte": datetime.utcnow() - timedelta(hours=24)},
            "reminder_sent": {"$ne": True}  # Ensure we don't send multiple reminders
        })
        
        for cart in inactive_carts:

            if "user_id" not in cart or not ObjectId.is_valid(cart["user_id"]):
                print(f"Invalid or missing user_id in cart: {cart['_id']}")
                continue

            user = user_collection.find_one({"_id": ObjectId(cart["user_id"])})

            cart_items = get_cart_items(cart["_id"])
            if not cart_items:
                print(f"No items found in cart: {cart['_id']}")
                continue

            # Prepare cart details for the email
            cart_details = ""
            cart_total = 0
            for item in cart_items:
                product = product_collection.find_one({"_id": ObjectId(item["product"]["_id"])})
                if product:
                    product_name = product.get("name", "Unknown Product")
                    quantity = item.get("quantity", 0)
                    subtotal = item.get("subtotal", 0)
                    cart_details += f"- {product_name} (x{quantity}): ${subtotal:.2f}\n"
                    cart_total += subtotal
            
            cart_link = config("SITE_URL") + "/cart"

            if user and user.get("email"):

                # Send reminder email
                send_mail(
                    subject="Don't forget your cart!",
                    message=(
                    f"Hi {user['name']},\n\n"
                    "You left some items in your cart. Here's what you have:\n\n"
                    f"{cart_details}\n"
                    f"Total: ${cart_total:.2f}\n\n"
                    f"Click here to view your cart: {cart_link}\n\n"
                    "Complete your purchase now before your items run out!"
                ),
                    from_email=config("DEFAULT_FROM_EMAIL"),
                    recipient_list=[user["email"]],
                    fail_silently=False,
                    
                )

                # Mark the cart as reminded
                carts_collection.update_one(
                    {"_id": cart["_id"]},
                    {"$set": {"reminder_sent": True}}
                )

        print("Cart reminder emails sent successfully.")

    except Exception as e:
        print(f"Error sending cart reminder emails: {str(e)}")

def notify_stock():
    try:
        carts = carts_collection.find()

        for cart in carts:
            if "user_id" not in cart or not ObjectId.is_valid(cart["user_id"]):
                print(f"Invalid or missing user_id in cart: {cart.get('_id')}")
                continue

            # Fetch the user associated with the cart
            user = user_collection.find_one({"_id": ObjectId(cart["user_id"])})
            if not user or not user.get("email"):
                print(f"User not found or missing email for cart: {cart.get('_id')}")
                continue

            # Fetch cart items
            cart_items = get_cart_items(cart["_id"])
            if not cart_items:
                print(f"No items found in cart: {cart.get('_id')}")
                continue

            # Check stock status for each product in the cart
            out_of_stock_products = []
            for item in cart_items:
                product = product_collection.find_one({"_id": ObjectId(item["product"]["_id"])})
                if product and product.get("stock", 0) <= 0:
                    out_of_stock_products.append(product.get("name", "Unknown Product"))

            # If there are out-of-stock products, send a notification email
            cart_link = config("SITE_URL") + "/cart"
            if out_of_stock_products:
                product_list = "\n".join(f"- {product}" for product in out_of_stock_products)
                send_mail(
                    subject="Some items in your cart are out of stock",
                    message=(
                        f"Hi {user['name']},\n\n"
                        "The following items in your cart are currently out of stock:\n\n"
                        f"{product_list}\n\n"
                        "Please visit your cart to update your items.\n\n"
                        f"Click here to view your cart: {cart_link}\n\n"
                        "Thank you for shopping with us!"
                    ),
                    from_email=config("DEFAULT_FROM_EMAIL"),
                    recipient_list=[user["email"]],
                    fail_silently=False,
                )

                print(f"Notification sent to {user['email']} for cart {cart['_id']}.")

    except Exception as e:
        print(f"Error notifying customers about out-of-stock products: {str(e)}")
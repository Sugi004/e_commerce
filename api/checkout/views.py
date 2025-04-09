from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from ..cart_management.cart_management_db import get_user_cart, get_cart_items
from django.http import JsonResponse
import stripe
from django.conf import settings
from django.urls import reverse
from django.contrib import messages
from django.core.mail import send_mail
from django.contrib import messages
from api.mongoDb import get_collection
from bson import ObjectId
import uuid
from datetime import datetime, timedelta

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY
users_collection = get_collection("users")

@csrf_exempt
def send_verification_email(email, verification_token, user_id):
    """Send verification email for checkout"""
    try:
        verification_url = f"{settings.SITE_URL}{reverse('verify_email', args=[verification_token, user_id])}"
        timeout = settings.EMAIL_VERIFICATION_TIMEOUT
        send_mail(
            subject='Verify Email to Complete Your Purchase - GlobalTech',
            message=f'''Please verify your email to complete your purchase.
            
Click here to verify: {verification_url}
            
This link expires in {timeout} minutes.''',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False
        )
        return True
    except Exception as e:
        print(f"Error sending verification email: {str(e)}")
        return False

@csrf_exempt
def checkout(request):
    COUPONS = {
    "SAVE10": 10,
    "FLAT50": 50,
    "FREESHIP": 0,
    "WELCOME20": 20,
    "SUMMER15": 15,
    "WINTER25": 25,
    "BLACKFRIDAY": 30,
    "CYBERMONDAY": 40,
    "HOLIDAY50": 50,
    "LOYALTY5": 5,
    }
    try:
        # Check for user_data in request or session
        session_id = request.GET.get('session_id')
        if session_id:
            checkout_session = stripe.checkout.Session.retrieve(session_id)
            print("checkout_session:", checkout_session)
        # # Retrieve user_id from client_reference_id
        user_id = checkout_session.get("client_reference_id")

        user_data = getattr(request,  'user_data', None) or request.session.get('user_data') or {"user_id": user_id}

        if not user_data:
            messages.warning(request, "Payment was cancelled. Please log in to view your cart.")
            return redirect("login_view")

        # Verify email before proceeding
        user = users_collection.find_one({"_id": ObjectId(user_data["user_id"])})
        if not user:
            messages.error(request, "User not found")
            return redirect('view_cart')

        # Get cart and process items
        cart = get_user_cart(user_id=user_data["user_id"])
        if not cart:
            return render(request, 'checkout.html', {
                "error": "No cart found",
                "cart_items": [],
                "cart_total": 0
            })

        # Verify email and send verification link if not verified
        if not user.get("is_verified"):
            verification_token = str(uuid.uuid4())
            users_collection.update_one(
                {"_id": user["_id"]},
                {
                    "$set": {
                        "verification_token": verification_token,
                        "verification_token_expires": datetime.utcnow() + timedelta(minutes=settings.EMAIL_VERIFICATION_TIMEOUT)
                    }
                }
            )

            if send_verification_email(user["email"], verification_token, str(user["_id"])):
                messages.info(request, "Please verify your email to complete checkout. Verification link sent.")
            else:
                messages.error(request, "Failed to send verification email. Please try again.")
            return redirect('view_cart')

        # Process cart for verified users
        cart_items = get_cart_items(cart["_id"])
        cart_total = 0

        for item in cart_items:
            product = item["product"]
            quantity = item["quantity"]
            price = float(product.get("price", 0))

            if product.get("discount"):
                discount = float(product["discount"]) / 100
                price = price * (1 - discount)

            item["subtotal"] = price * quantity
            cart_total += item["subtotal"]
        
        # Apply 10% discount for cart total over $100
        if cart_total > 100:
            cart_total -= cart_total * 0.1 

        # Calculate shipping cost, free shipping for orders more than $50
        shipping_cost = 0 if cart_total > 50 else 10.00

        # Handle coupon code
        coupon_code = request.POST.get("coupon_code", "").strip().upper()
        coupon_discount = 0
        if coupon_code:
            if coupon_code in COUPONS:
                discount_value = COUPONS[coupon_code]
                if discount_value > 0:
                    if discount_value < 100:  # Percentage discount
                        coupon_discount = cart_total * (discount_value / 100)
                    else:  # Flat discount
                        coupon_discount = discount_value
                    messages.success(request, f"Coupon '{coupon_code}' applied successfully!")
                else:
                    # Handle free shipping coupon
                    shipping_cost = 0
                    messages.success(request, f"Coupon '{coupon_code}' applied successfully! Free shipping applied.")
            else:
                messages.error(request, "Invalid coupon code.")
        
        # Ensure discount does not exceed cart total
        coupon_discount = min(coupon_discount, cart_total)
        cart_total -= coupon_discount

        context = {
            "cart_items": cart_items,
            "cart_total": round(cart_total, 2),
            "shipping_cost": round(shipping_cost, 2),
            "total_with_shipping": round(cart_total + shipping_cost, 2),
            "stripe_public_key": settings.STRIPE_PUBLIC_KEY,
            "user": user,
            "coupon_discount": round(coupon_discount, 2),
        }

        return render(request, 'checkout.html', context)

    except Exception as e:
        print(f"Error in checkout: {str(e)}")
        return render(request, 'checkout.html', {"error": str(e)})

@csrf_exempt
def payment_success(request):
    try:
        # Retrieve user data
        user_data = getattr(request, 'user_data', None) or request.session.get('user_data')
        if not user_data:
            messages.error(request, "User not found. Please log in again.")
            return redirect('login_view')

        user = users_collection.find_one({"_id": ObjectId(user_data["user_id"])})
        if not user:
            messages.error(request, "User not found.")
            return redirect('checkout')

        # Retrieve cart and calculate total
        cart = get_user_cart(user_id=user_data["user_id"])
        if not cart:
            messages.error(request, "No cart found.")
            return redirect('checkout')

        cart_items = get_cart_items(cart["_id"])
        cart_total = sum(item["subtotal"] for item in cart_items)

        # Apply 10% discount if cart total exceeds $100
        if cart_total > 100:
            cart_total -= cart_total * 0.1

        # Add loyalty points (2% of cart total)
        loyalty_points = round(cart_total * 0.02, 2)
        users_collection.update_one(
            {"_id": user["_id"]},
            {"$inc": {"loyalty_points": loyalty_points}}
        )

        # Clear the cart after successful payment
        cart_items_collection = get_collection("cart_items")
        cart_items_collection.delete_many({"cart_id": cart["_id"]})

        messages.success(request, f"Payment successful! You earned {loyalty_points} loyalty points.")
        return render(request, 'payment_success.html', {"loyalty_points": loyalty_points})

    except Exception as e:
        print(f"Error in payment_success: {str(e)}")
        messages.error(request, "An error occurred while processing your payment.")
        return redirect('checkout')

@csrf_exempt
def payment_cancel(request):
    try:
        # Retrieve the session_id from the query parameters
        session_id = request.GET.get('session_id')
        # Retrieve the Stripe session
        checkout_session = stripe.checkout.Session.retrieve(session_id)

        # Retrieve user_id from client_reference_id
        user_id = checkout_session.get("client_reference_id")

        user = users_collection.find_one({"_id": ObjectId(user_id)})

        # Notify the user that the payment was cancelled
        messages.warning(request, f"Payment was cancelled. Your cart items are still saved.")
        return redirect(f"/checkout/?session_id={session_id}")

    except Exception as e:
        print(f"Error in payment_cancel: {str(e)}")
        messages.error(request, "An unexpected error occurred. Please try again.")
        return redirect("checkout")

@csrf_exempt
def process_payment(request):
    if request.method != "POST":
        messages.error(request, "Invalid request method")
        return redirect('checkout')

    try:
        cart_total = float(request.POST.get("cart_total", 0))
        shipping_cost = float(request.POST.get("shipping_cost", 0))
        coupon_discount = float(request.POST.get("coupon_discount", 0))

        cart = get_user_cart(user_id=request.user_data["user_id"]) if request.user_data else get_user_cart(session_id=request.session.session_key)
        if not cart:
            messages.error(request, "No cart found")
            return redirect('checkout')

        cart_items = get_cart_items(cart["_id"])
       

        total = cart_total - coupon_discount + shipping_cost
        
        line_items = [{
            'price_data': {
                'currency': 'usd',
                'unit_amount': int(total * 100),
                'product_data': {
                    'name': 'Order Total',
                    'description': 'Includes all items, discounts, and shipping',
                },
            },
            'quantity': 1,
        }]


        # Create Stripe checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url=request.build_absolute_uri(reverse('payment_success')) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=request.build_absolute_uri(reverse('payment_cancel')) + '?session_id={CHECKOUT_SESSION_ID}',
            billing_address_collection='required',
            shipping_address_collection={
                'allowed_countries': ['US'],
            },
            client_reference_id=request.user_data["user_id"],
        )

        if not checkout_session or not checkout_session.id:
            messages.error(request, "Failed to create checkout session")
            return redirect('checkout')

        # If successful, redirect to Stripe's checkout page
        return redirect(checkout_session.url)

    except stripe.error.StripeError as e:
        messages.error(request, f"Payment processing failed: {str(e)}")
        return redirect('checkout')
    except Exception as e:
        messages.error(request, "An unexpected error occurred. Please try again.")
        return redirect('checkout')

from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from ..cart_management.cart_management_db import get_user_cart, get_cart_items
from django.http import JsonResponse
import stripe
from django.conf import settings
from django.urls import reverse
from django.contrib import messages

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

@csrf_exempt
def checkout(request):
    """Handle checkout page rendering"""
    try:
        cart = get_user_cart(user_id=request.user_data["_id"]) if request.user_data else get_user_cart(session_id=request.session.session_key)
        
        if not cart:
            return render(request, 'checkout.html', {
                "error": "No cart found",
                "cart_items": [],
                "cart_total": 0
            })

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

        context = {
            "cart_items": cart_items,
            "cart_total": round(cart_total, 2),
            "shipping_cost": 10.00,
            "total_with_shipping": round(cart_total + 10.00, 2),
            "stripe_public_key": settings.STRIPE_PUBLIC_KEY
        }

        return render(request, 'checkout.html', context)

    except Exception as e:
        print(f"Error in checkout: {str(e)}")
        return render(request, 'checkout.html', {"error": str(e)})

@csrf_exempt
def payment_success(request):
    """Handle successful payment"""
    return render(request, 'payment_success.html')

@csrf_exempt
def payment_cancel(request):
    """Handle cancelled payment"""
    return render(request, 'payment_cancel.html')

@csrf_exempt
def process_payment(request):
    """Handle payment processing through Stripe"""
    if request.method != "POST":
        messages.error(request, "Invalid request method")
        return redirect('checkout')

    try:
        cart = get_user_cart(user_id=request.user_data["_id"]) if request.user_data else get_user_cart(session_id=request.session.session_key)
        if not cart:
            messages.error(request, "No cart found")
            return redirect('checkout')
        cart_items = get_cart_items(cart["_id"])
        line_items = []
        
        # Prepare line items for Stripe
        for item in cart_items:
            price = float(item["product"].get("price", 0))
            if item["product"].get("discount"):
                discount = float(item["product"]["discount"]) / 100
                price = price * (1 - discount)

            line_item = {
                'price_data': {
                    'currency': 'usd',
                    'unit_amount': int(price * 100),
                    'product_data': {
                        'name': item["product"]["name"],
                    },
                },
                'quantity': item["quantity"],
            }

            # Only add description if it exists
            if item["product"].get("description"):
                line_item['price_data']['product_data']['description'] = item["product"]["description"]

            line_items.append(line_item)

        # Add shipping cost
        line_items.append({
            'price_data': {
                'currency': 'usd',
                'unit_amount': 1000,
                'product_data': {
                    'name': 'Shipping',
                    'description': 'Standard shipping',
                },
            },
            'quantity': 1,
        })

        # Create Stripe checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url=request.build_absolute_uri(reverse('payment_success')),
            cancel_url=request.build_absolute_uri(reverse('payment_cancel')),
            billing_address_collection='required',
            shipping_address_collection={
                'allowed_countries': ['US'],
            },
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

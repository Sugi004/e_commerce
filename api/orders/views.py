from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.contrib import messages
from api.mongoDb import get_collection
from bson import ObjectId
from datetime import datetime


@csrf_exempt
def my_orders(request):
    try:
        # Retrieve user data
        user_data = getattr(request, 'user_data', None) or request.session.get('user_data')
        if not user_data:
            messages.error(request, "User not found. Please log in again.")
            return redirect('login/login_view')

        # Fetch orders for the user
        orders_collection = get_collection("orders")
        orders = list(orders_collection.find({"user_id": ObjectId(user_data["user_id"])}))

        for order in orders:
            order["id"] = str(order["_id"])

        non_cancellable_statuses = ["Shipped", "Delivered", "Cancelled"]

        # Render the orders page
        return render(request, 'order_management/orders.html', {"orders": orders, "non_cancellable_statuses": non_cancellable_statuses})

    except Exception as e:
        print(f"Error in my_orders: {str(e)}")
        messages.error(request, "An unexpected error occurred. Please try again.")
        return redirect('checkout')
    
@csrf_exempt
def track_order(request, order_id):
    try:
        # Retrieve the order by ID
        order = get_collection("orders").find_one({"_id": ObjectId(order_id)})
        if not order:
            messages.error(request, "Order not found.")
            return redirect("my_orders")  # Redirect to the "My Orders" page

        # Get the current order status
        order_status = order.get("order_status", "Unknown")

        # Render the order status page
        return render(request, "order_management/track_order.html", {"order_id": order_id, "order_status": order_status})

    except Exception as e:
        print(f"Error in track_order: {str(e)}")
        messages.error(request, "An unexpected error occurred. Please try again.")
        return redirect("my_orders") 

@csrf_exempt
def cancel_order(request, order_id):
    try:
        # Retrieve the order by ID
        order = get_collection("orders").find_one({"_id": ObjectId(order_id)})
        if not order:
            messages.error(request, "Order not found.")
            return redirect("my_orders")  # Redirect to the "My Orders" page

        # Check if the order can be cancelled
        if order.get("order_status") in ["Shipped", "Delivered"]:
            messages.error(request, "Order cannot be cancelled after it is shipped or delivered.")
            return redirect("my_orders")

        # Update the order status to "Cancelled"
        get_collection("orders").update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {"order_status": "Cancelled", "updated_at": datetime.utcnow()}}
        )
        messages.success(request, "Order cancelled successfully.")
        return redirect("my_orders")

    except Exception as e:
        print(f"Error in cancel_order: {str(e)}")
        messages.error(request, "An unexpected error occurred. Please try again.")
        return redirect("my_orders")
@csrf_exempt
def request_refund(request, order_id):
    try:
        # Retrieve the order by ID
        order = get_collection("orders").find_one({"_id": ObjectId(order_id)})
        if not order:
            messages.error(request, "Order not found.")
            return redirect("my_orders")  # Redirect to the "My Orders" page

        # Check if the order is eligible for a refund
        if order.get("order_status") in ["Cancelled", "Refunded"]:
            messages.error(request, "Refund cannot be requested for this order.")
            return redirect("my_orders")

        if request.method == "POST":
            # Get the refund reason from the form
            reason = request.POST.get("reason", "").strip()
            if not reason:
                messages.error(request, "Please provide a reason for the refund request.")
                return redirect("my_orders")

            # Add refund request to the database
            refund_request = {
                "order_id": ObjectId(order_id),
                "reason": reason,
                "status": "Pending",
                "requested_at": datetime.utcnow(),
            }
            get_collection("refund_requests").insert_one(refund_request)

            # Update the order status to "Refund Requested"
            get_collection("orders").update_one(
                {"_id": ObjectId(order_id)},
                {"$set": {"order_status": "Refund Requested", "updated_at": datetime.utcnow()}}
            )

            messages.success(request, "Refund request submitted successfully.")
            return redirect("my_orders")

        # Render the refund request form
        return render(request, "order_management/request_refund.html", {"order_id": order_id})

    except Exception as e:
        print(f"Error in request_refund: {str(e)}")
        messages.error(request, "An unexpected error occurred. Please try again.")
        return redirect("my_orders")
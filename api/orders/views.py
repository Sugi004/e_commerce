from ..modules import *
from .order_schema import RefundRequestSchema
from marshmallow import ValidationError
from ..utils.date_utils import validate_and_convert_dates

@csrf_exempt
def my_orders(request):
    try:
        # Retrieve user data
        user_data = getattr(request, 'user_data', None) or request.session.get('user_data')
        if not user_data:
            messages.error(request, "User not found. Please log in again.")
            return redirect('login/login_view')

        # Fetch orders for the user
        orders = list(orders_collection.find({"user_id": ObjectId(user_data["user_id"])}))

        for order in orders:
            order["id"] = str(order["_id"])
            for item in order.get("items", []):
                product = products_collection.find_one({"_id": ObjectId(item["product_id"])})
                item["product_name"] = product["name"] if product else "Unknown Product"

        non_cancellable_statuses = ["Shipped", "Delivered", "Cancelled"]

        # Render the orders page
        return render(request, 'order_management/orders.html',
                      {"orders": orders,
                       "non_cancellable_statuses": non_cancellable_statuses
                       })

    except Exception as e:
        print(f"Error in my_orders: {str(e)}")
        messages.error(request, "An unexpected error occurred. Please try again.")
        return redirect('checkout')
    
@csrf_exempt
def track_order(request, order_id):
    try:
        order = get_collection("orders").find_one({"_id": ObjectId(order_id)})
        if not order:
            messages.error(request, "Order not found.")
            return redirect("my_orders")

        order_status = order.get("status", order.get("order_status", "Unknown")).lower()
        created_at = order.get("created_at")
        if not created_at:
            created_at = datetime.utcnow()  # fallback if missing

        # Ensure created_at is a datetime object
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        timeline = [
            {"status": "Order Placed", "timestamp": created_at.strftime("%Y-%m-%d %H:%M"), "note": "Order placed"}
        ]

        if order_status == "pending":
            timeline.append({
                "status": "Pending",
                "timestamp": (created_at + timedelta(days=1)).strftime("%Y-%m-%d %H:%M"),
                "note": "Awaiting processing"
            })
        elif order_status == "shipped":
            timeline.append({
                "status": "Processed",
                "timestamp": (created_at + timedelta(days=1)).strftime("%Y-%m-%d %H:%M"),
                "note": "Order processed"
            })
            timeline.append({
                "status": "Shipped",
                "timestamp": (created_at + timedelta(days=3)).strftime("%Y-%m-%d %H:%M"),
                "note": "Shipped via DHL, tracking #12345"
            })
        elif order_status == "delivered":
            timeline.append({
                "status": "Processed",
                "timestamp": (created_at + timedelta(days=1)).strftime("%Y-%m-%d %H:%M"),
                "note": "Order processed"
            })
            timeline.append({
                "status": "Shipped",
                "timestamp": (created_at + timedelta(days=3)).strftime("%Y-%m-%d %H:%M"),
                "note": "Shipped via DHL, tracking #12345"
            })
            timeline.append({
                "status": "Delivered",
                "timestamp": (created_at + timedelta(days=6)).strftime("%Y-%m-%d %H:%M"),
                "note": "Delivered to address"
            })
        elif order_status == "cancelled":
            timeline.append({
                "status": "Cancelled",
                "timestamp": (created_at + timedelta(days=1)).strftime("%Y-%m-%d %H:%M"),
                "note": "Order was cancelled"
            })

        return render(request, "order_management/track_order.html", {
            "order_id": order_id,
            "status": order.get("status", order.get("order_status", "Unknown")),
            "tracking_history": timeline
        })

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
                "user_id": ObjectId(order["user_id"]),
                "amount": order.get("total_price", 0.0),  # Assuming total price is the refund amount
                "reason": reason,
                "status": "Pending",
                "requested_at": datetime.utcnow(),
            }
            refund_schema = RefundRequestSchema()
            

            refund_request = validate_and_convert_dates(refund_request, ["requested_at"])
           
            # Validate the refund request data

            try:
                validated_refund = refund_schema.load(refund_request)
            except ValidationError as e:
                print(f"Refund validation error: {e.messages}")
                messages.error(request, "Failed to submit refund request.")
                return redirect("my_orders")
            # Insert the validated data in database
            get_collection("refund_requests").insert_one(validated_refund)

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
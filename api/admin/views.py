from ..modules import *
from django.core.paginator import Paginator

def render_users_admin(request):
    """Render the admin user management page."""
    try:
        if not request.user_data:
            messages.error(request, "Session expired. Please log in to access this page.")
            return render(request, "login/login.html")
        # Check if the user is authenticated and has admin role
        if request.user_data.get("role") != "admin":
            messages.error(request, "Access denied. Admin privileges required.")
            return render(request, "error.html")

        # Fetch users from the database
        users = list(users_collection.find())

        transformed_users = []
        for user in users:
            transformed_user = {
                "id": str(user.get("_id", "")),  # Ensure 'id' is set correctly
                "name": user.get("name", ""),
                "email": user.get("email", ""),
                "role": user.get("role", ""),
                "is_active": user.get("is_active", False),
                "created_at": user.get("created_at", ""),
            }
            transformed_users.append(transformed_user)

        # Render the admin user management page
        return render(request, "admin/users.html", {
            "users": transformed_users,
            "admin_name": request.user_data.get("email"),
        })

    except Exception as e:
        # Handle errors and render the error page
        print(f"Error in render_users_admin: {str(e)}")
        messages.error(request, f"An error occurred: {str(e)}")
        return render(request, "error.html")

def render_admin_panel(request):
    """Render the admin panel."""
    try:
        if not request.user_data or request.user_data.get("role") != "admin":
            return render(request, "error.html",  )
        return render(request, "admin/admin.html")
    except Exception as e:
        print(f"Error in render_admin_panel: {str(e)}")
        return render(request, "error.html", {"error": str(e)})

def manage_coupons(request):
    try:
        if not request.user_data or request.user_data.get("role") != "admin":
            messages.error(request, "Access denied. Admin privileges required.")
            return render(request, "error.html",  )

        selected_coupon = None

        if request.method == "GET" and "edit_coupon_id" in request.GET:
            # Fetch the selected coupon for editing
            coupon_id = request.GET.get("edit_coupon_id")
            if ObjectId.is_valid(coupon_id):
                selected_coupon = coupons_collection.find_one({"_id": ObjectId(coupon_id)})
                if selected_coupon:
                    selected_coupon["id"] = str(selected_coupon["_id"])

        if request.method == "POST":
            # Handle coupon creation or modification
            coupon_id = request.POST.get("coupon_id")
            code = request.POST.get("code")
            discount_percentage = float(request.POST.get("discount_percentage", 0))
            expiry_date = request.POST.get("expiry_date")
            is_active = request.POST.get("is_active") == "on"

            if coupon_id and ObjectId.is_valid(coupon_id):
                # Update existing coupon
                coupons_collection.update_one(
                    {"_id": ObjectId(coupon_id)},
                    {"$set": {
                        "code": code,
                        "discount_percentage": discount_percentage,
                        "expiry_date": expiry_date,
                        "is_active": is_active,
                        "updated_at": datetime.utcnow()
                    }}
                )
                messages.success(request, "Coupon updated successfully.")
            else:
                # Create new coupon
                coupons_collection.insert_one({
                    "code": code,
                    "discount_percentage": discount_percentage,
                    "expiry_date": expiry_date,
                    "is_active": is_active,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                })
                messages.success(request, "Coupon created successfully.")

            return redirect("manage_coupons")

        # Fetch all coupons for display
        coupons = list(coupons_collection.find())
        for coupon in coupons:
            coupon["id"] = str(coupon["_id"])

        return render(request, "admin/manage_coupons.html", {
            "coupons": coupons,
            "selected_coupon": selected_coupon
        })

    except Exception as e:
        print(f"Error in manage_coupons: {str(e)}")
        return render(request, "error.html", {"error": str(e)})

def view_refund_requests(request):
    """View to display and manage refund requests."""
    try:
        if not request.user_data or request.user_data.get("role") != "admin":
            messages.error(request, "Access denied. Admin privileges required.")
            return render(request, "error.html")

        user = None

        if request.method == "POST":
            refund_id = request.POST.get("refund_id")
            action = request.POST.get("action")

            if refund_id and ObjectId.is_valid(refund_id):
                status = "approved" if action == "approve" else "rejected"
                refund_requests_collection.update_one(
                    {"_id": ObjectId(refund_id)},
                    {"$set": {
                        "status": status,
                        "updated_at": datetime.utcnow()
                    }}
                )
                messages.success(request, f"Refund request {status} successfully.")

            return redirect("view_refund_requests")

        # Fetch all refund requests
        refund_requests = list(refund_requests_collection.find())
        for refund in refund_requests:
            refund["id"] = str(refund["_id"])
            user = users_collection.find_one({"_id": ObjectId(refund["user_id"])})
            refund["user_name"] = user["name"] if user else "Unknown User"
            refund["amount"] = refund.get("amount", 0)
            refund["requested_at"] = refund.get("requested_at", datetime.utcnow())

        return render(request, "admin/refund_requests.html", {
            "refund_requests": refund_requests,
        })

    except Exception as e:
        print(f"Error in view_refund_requests: {str(e)}")
        return render(request, "error.html", {"error": str(e)})

def moderate_reviews(request):
    try:
        # Ensure the user is an admin
        if not request.user_data or request.user_data.get("role") != "admin":
            messages.error(request, "Access denied. Admin privileges required.")
            return render(request)

        if request.method == "POST":
            # Handle review approval, rejection, or deletion
            review_id = request.POST.get("review_id")
            action = request.POST.get("action")  

            if review_id and ObjectId.is_valid(review_id):
                # Fetch the review by its ID
                review = reviews_collection.find_one({"reviews.id": ObjectId(review_id)})
                if not review:
                    messages.error(request, "Review not found.")
                    return redirect("moderate_reviews")

                if action == "delete":
                    # Delete the review
                    reviews_collection.update_one(
                        {"reviews.id": ObjectId(review_id)},
                        {"$pull": {"reviews": {"id": ObjectId(review_id)}}}
                    )
                    messages.success(request, "Review deleted successfully.")
                else:
                    # Approve or reject the review
                    status = "approved" if action == "approve" else "rejected"
        
                    review_document = reviews_collection.find_one({"reviews.id": ObjectId(review_id)})
                    reviews_collection.update_one(
                    {"reviews.id": ObjectId(review_id)},
                    {"$set": {
                        "reviews.$.status": status,
                        "reviews.$.updated_at": datetime.utcnow()
                    }})
                    messages.success(request, f"Review {status} successfully.")

            return redirect("moderate_reviews")

        # Fetch all reviews
        reviews = list(reviews_collection.find())
        total_reviews = 0

        for review in reviews:
            review["id"] = str(review["_id"])  # Convert ObjectId to string
            product = products_collection.find_one({"_id": ObjectId(review["product_id"])})
            review["product_name"] = product["name"] if product else "Unknown Product"
            
            if "reviews" in review and isinstance(review["reviews"], list):
                total_reviews += len(review["reviews"])
        
        return render(request, "admin/reviews.html", {
            "reviews": reviews,
            "total_reviews": total_reviews
        })
        

    except Exception as e:
        print(f"Error in moderate_reviews: {str(e)}")
        return render(request, "error.html", {"error": str(e)})

def manage_categories(request):
    try:
        if not request.user_data or request.user_data.get("role") != "admin":
            messages.error(request, "Access denied. Admin privileges required.")
            return render(request, "error.html")

        if request.method == "POST":
            # Handle category or tag creation, update, or deletion
            action = request.POST.get("action")  # "add_category", "edit_category", "delete_category", etc.
            item_type = request.POST.get("item_type")  # "category" or "tag"
            old_name = request.POST.get("old_name")  # For renaming categories or tags
            new_name = request.POST.get("new_name")  # For adding or renaming categories or tags

            if action == "add" and new_name:
                # Add a new category or tag
                if item_type == "category":
                    # Ensure the category is added to at least one product
                    products_collection.update_one(
                        {"category": {"$ne": new_name}},  # Check if the category doesn't already exist
                        {"$set": {"category": new_name}},
                        upsert=True
                    )
                elif item_type == "tag":
                    # Add the tag to at least one product
                    products_collection.update_one(
                        {"tags": {"$ne": new_name}},  # Check if the tag doesn't already exist
                        {"$push": {"tags": new_name}},
                        upsert=True
                    )
                messages.success(request, f"{item_type.capitalize()} '{new_name}' added successfully.")

            elif action == "rename" and old_name and new_name:
                # Rename an existing category or tag
                if item_type == "category":
                    products_collection.update_many(
                        {"category": old_name},
                        {"$set": {"category": new_name}}
                    )
                elif item_type == "tag":
                    products_collection.update_many(
                        {"tags": old_name},
                        {"$set": {"tags.$": new_name}}  # Update the specific tag in the array
                    )
                messages.success(request, f"{item_type.capitalize()} '{old_name}' renamed to '{new_name}' successfully.")

            elif action == "delete" and old_name:
                # Delete a category or tag
                if item_type == "category":
                    products_collection.update_many(
                        {"category": old_name},
                        {"$unset": {"category": ""}}
                    )
                elif item_type == "tag":
                    products_collection.update_many(
                        {"tags": old_name},
                        {"$pull": {"tags": old_name}}
                    )
                messages.success(request, f"{item_type.capitalize()} '{old_name}' deleted successfully.")

            return redirect("manage_categories")

        # Fetch all unique categories and tags
        categories = products_collection.distinct("category")
        tags = products_collection.distinct("tags")

        return render(request, "admin/manage_categories.html", {
            "categories": categories,
            "tags": tags
        })

    except Exception as e:
        print(f"Error in manage_categories_tags: {str(e)}")
        return render(request, "error.html", {"error": str(e)})

def manage_products(request):
    """Render the admin manage products page with search, edit, and delete options."""
    try:
        # Ensure only admins can access
        if not request.user_data or request.user_data.get("role") != "admin":
            messages.error(request, "Access denied. Admin privileges required.")
            return render(request)

        search_query = request.GET.get("search", "").strip()
        products = []

        if search_query:
            # Search products by name (case-insensitive)
            products = list(products_collection.find({
                "name": {"$regex": search_query, "$options": "i"}
            }))
        else:
            # Show all products by default (or limit for performance)
            products = list(products_collection.find())

        # Convert ObjectId to string for template usage
        for product in products:
            product["id"] = str(product.get("_id", ""))

        # Handle pagination
        paginator = Paginator(products, 30)  # 30 products per page
        page_number = request.GET.get('page', 1)


        return render(request, "admin/manage_products.html", {
            "products": products,
            "search_query": search_query,
            "page_obj": paginator.get_page(page_number),
            "paginator": paginator,
        })

    except Exception as e:
        print(f"Error in render_manage_products: {str(e)}")
        return render(request, "error.html", {"error": str(e)})


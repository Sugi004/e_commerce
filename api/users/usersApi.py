from ..modules import *
from .userSchema import UserSchema
from django.contrib.auth.hashers import make_password
from ..checkout.views import send_verification_email


def create_user(request):
    """API to create a new user."""
    if request.method == "POST":
        try:
            # Extract data from the form
            data = request.POST.dict()
            data.pop("csrfmiddlewaretoken", None)

            schema = UserSchema()
            validated_data = schema.load(data)
            validated_data["role"] = validated_data.get("role", "customer")

            # Check for duplicate email or name
            if users_collection.find_one({"email": validated_data["email"]}):
                messages.error(request, "Email already exists")
                return redirect("sign_up")
            if users_collection.find_one({"name": validated_data["name"]}):
                messages.error(request, "Name already exists")
                return redirect("sign_up")

            # Restrict the number of admin users
            if validated_data["role"] == "admin" and users_collection.count_documents({"role": "admin"}) >= 3:
                messages.error(request, "Only a maximum of 3 admin users are allowed")
                return redirect("sign_up")

            # Hash the password and save the user
            validated_data["password"] = make_password(validated_data["password"])
            validated_data["created_at"] = datetime.utcnow()
            users_collection.insert_one(validated_data)

            messages.success(request, "User created successfully. Please sign in.")
            return redirect("login_view")

        except ValidationError as err:
            messages.error(request, f"Validation error: {err.messages}")
            return redirect("sign_up")
        except Exception as e:
            messages.error(request, f"Error creating user: {str(e)}")
            return redirect("sign_up")

    messages.error(request, "Invalid request method")
    return redirect("sign_up")


def update_user(request, user_id):
    """Update user details (Admin-only: lock, suspend, role change)."""
    if request.method == "POST" and request.POST.get('_method') == 'PUT':
        try:
            # Extract data from the form
            data = request.POST.dict()

            update_data = {}
            if "is_locked" in data:
                update_data["is_locked"] = data["is_locked"]
            if "is_active" in data:
                update_data["is_active"] = data["is_active"].lower() == "true"
            if "role" in data:
                update_data["role"] = data["role"].lower()
            if "name" in data:
                update_data["name"] = data["name"]
            if "email" in data:
                update_data["email"] = data["email"]
            if "password" in data:
                update_data["password"] = make_password(data["password"])

            if not update_data:
                messages.error(request, "No valid fields to update")
                return redirect("render_users_admin")

            result = users_collection.update_one({"_id": ObjectId(user_id)}, {"$set": update_data})
            if result.matched_count == 0:
                messages.error(request, "User not found")
                return redirect("render_users_admin")

            messages.success(request, "User updated successfully")
            return redirect("render_users_admin")

        except Exception as e:
            messages.error(request, f"Error updating user: {str(e)}")
            return redirect("render_users_admin")

    messages.error(request, "Invalid request method")
    return render(request, "error.html")


def delete_user(request, user_id):
    """Delete a user (Admin-only)."""
    if request.method == 'POST' and request.POST.get('_method') == 'DELETE':
        try:
            result = users_collection.delete_one({"_id": ObjectId(user_id)})
            if result.deleted_count == 0:
                messages.error(request, "User not found")
                return redirect("render_products")

            messages.success(request, "User deleted successfully")
            return redirect("render_products")

        except Exception as e:
            messages.error(request, f"Error deleting user: {str(e)}")
            return redirect("render_products")

    messages.error(request, "Invalid request method")
    return render(request, "error.html")


def verify_email(request, token, user_id):
    """Verify user email address."""
    try:
        if not token or not user_id:
            messages.error(request, "Invalid verification link")
            return redirect('login_view')

        # Find user with valid verification token
        user = users_collection.find_one({
            "verification_token": token,
            "verification_token_expires": {"$gt": datetime.utcnow()}
        })

        if not user:
            messages.error(request, "Invalid or expired verification token")
            return render(request, 'error.html')

        # Update user verification status
        users_collection.update_one(
            {"_id": user["_id"]},
            {
                "$set": {"is_verified": True},
                "$unset": {"verification_token": "", "verification_token_expires": ""}
            }
        )

        request.session['user_data'] = {
            "user_id": str(user["_id"]),
            "email": user["email"],
            "role": user.get("role", "customer")
        }
        request.session.save()

        messages.success(request, "Email verified successfully. You can now complete your purchase.")
        return redirect('checkout')

    except Exception as e:
        messages.error(request, f"Verification failed: {str(e)}")
        return redirect("checkout")


def resend_verification(request):
    """Resend verification email to user."""
    try:
        if not request.user_data:
            messages.error(request, "Please login to continue")
            return redirect('login_view')

        user = users_collection.find_one({"_id": ObjectId(request.user_data["user_id"])})

        if not user:
            messages.error(request, "User not found")
            return redirect('checkout')

        if user.get("is_verified"):
            messages.info(request, "Your email is already verified")
            return redirect('checkout')

        # Generate new verification token
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

        # Send verification email
        if send_verification_email(user["email"], verification_token):
            messages.success(request, "Verification email sent. Please check your inbox.")
        else:
            messages.error(request, "Failed to send verification email. Please try again.")

        return redirect('checkout')

    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect('checkout')

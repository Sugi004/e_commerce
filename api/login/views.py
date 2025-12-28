from ..modules import *
from django.contrib.auth.hashers import check_password, make_password
import jwt
from django.utils.timezone import make_aware, now


def is_json_request(request):
    return request.content_type == 'application/json'

@csrf_exempt
def login_view(request):
    if request.method == "POST":
        try:
            # Get email and password from the request
            email = request.POST.get("email", "").strip()
            password = request.POST.get("password", "").strip()

            if not email or not password:
                messages.error(request, "Email and password are required")
                return render(request, 'login/login.html')

            # Fetch user from the database
            user = users_collection.find_one({"email": email})
            print(user)
            if not user:
                messages.error(request, "Invalid credentials")
                return render(request, 'login/login.html')

            # Check if the user is locked out due to failed attempts
            failed_attempts = user.get("failed_attempts", 0)
            if failed_attempts >= 3: # Assuming 3 failed attempts lock the user out
                reset_token = str(uuid.uuid4())
                reset_url = f"{config('SITE_URL')}{reverse('password_reset', args=[reset_token])}"
                send_mail(
                    subject="Password Reset Request",
                    message=f"Click the link below to reset your password:\n\n{reset_url}",
                    from_email=config('DEFAULT_FROM_EMAIL'),
                    recipient_list=[email],
                    fail_silently=False,
                )
                users_collection.update_one(
                    {"_id": user["_id"]},
                    {"$set": {"reset_token": reset_token, "reset_token_expires": now() + timedelta(hours=1)}}
                )
                messages.error(request, "Too many failed login attempts. A password reset link has been sent to your email.")
                return redirect("login_view")

            # Verify hashed password
            stored_hashed_password = user.get("password")
            if not check_password(password, stored_hashed_password):
                # Increment failed attempts
                users_collection.update_one(
                    {"_id": user["_id"]},
                    {"$inc": {"failed_attempts": 1}, "$set": {"last_failed_attempt": now()}}
                )
                messages.error(request, "Invalid credentials")
                return render(request, 'login/login.html')

            # Reset failed attempts on successful login
            users_collection.update_one({"_id": user["_id"]}, {"$set": {"failed_attempts": 0}})

            # Create JWT payload
            payload = {
                "user_id": str(user["_id"]),
                "email": user["email"],
                "role": user.get("role", "guest"),
                "exp": datetime.now() + timedelta(hours=24)
            }

            # Generate JWT token
            secret_key = config('SECRET_KEY')
            token = jwt.encode(payload, secret_key, algorithm="HS256")

            # Set session data
            request.session["user_id"] = str(user["_id"])
            request.session["role"] = payload["role"]

            # Set cookie
            response = redirect("render_products")
            response.set_cookie(
                key="access_token",
                value=token,
                httponly=True,
                secure=True,
                samesite="Strict"
            )

            messages.success(request, "Login successful")
            return response

        except Exception as e:
            messages.error(request, f"An unexpected error occurred: {str(e)}")
            return render(request, 'login/login.html')

    return render(request, 'login/login.html')


def logout_view(request):
    request.session.flush()
    response = redirect('render_products')
    response.delete_cookie('access_token')
    messages.success(request, "Logged out successfully")
    return response


def sign_up(request):
    return render(request, 'login/sign_up.html')


@csrf_exempt
def password_reset(request, reset_token):
    """Handle password reset"""
    try:
        if request.method == "POST":
            new_password = request.POST.get("new_password")

            # Find user by reset token
            user = users_collection.find_one({"reset_token": reset_token})
            if not user:
                messages.error(request, "Invalid or expired reset token.")
                return redirect("login_view")

            # Convert reset_token_expires to timezone-aware if it's naive
            reset_token_expires = user.get("reset_token_expires")
            if reset_token_expires and reset_token_expires.tzinfo is None:
                reset_token_expires = make_aware(reset_token_expires)

            # Check if the reset token is expired
            if not reset_token_expires or reset_token_expires < now():
                messages.error(request, "Invalid or expired reset token.")
                return redirect("login_view")

            # Hash the new password
            new_password = make_password(new_password)

            # Update the user's password
            users_collection.update_one(
                {"_id": user["_id"]},
                {"$set": {"password": new_password, 
                          "reset_token": None, 
                          "reset_token_expires": None,
                          "failed_attempts": 0}}
            )
            messages.success(request, "Your password has been reset successfully. Please log in.")
            return redirect("login_view")

        return render(request, "login/password_reset.html", {"reset_token": reset_token})

    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return redirect("login_view")
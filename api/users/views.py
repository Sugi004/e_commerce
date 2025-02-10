from django.shortcuts import render
from .usersApi import get_users

def render_users_admin(request):
    """Fetch user data from API and display in HTML (Admin-only)"""
    try:
        # Simulate authentication (Replace with real authentication)
        admin_role = "admin"

        if admin_role.lower() != "admin":
            return render(request, "error.html", {"error": "Access denied. Admins only."})

        # Fetch user data from the JSON API
        response = get_users(request)

        if response.status_code == 200:
            users = response.json()
        else:
            users = []

        return render(request, "users.html", {"users": users})

    except Exception as e:
        return render(request, "error.html", {"error": str(e)})


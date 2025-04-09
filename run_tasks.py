import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'e_commerce.settings')
django.setup()

from api.cart_management.views import send_cart_reminder_emails, notify_stock

if __name__ == "__main__":
    print("Running scheduled tasks...")
    # Run notification tasks
    try:
        print("Running notify_stock...")
        notify_stock()
        print("notify_stock completed successfully.")
    except Exception as e:
        print(f"Error in notify_stock: {str(e)}")

    # Run the send reminder email function
    try:
        print("Running send_cart_reminder_emails...")
        send_cart_reminder_emails()
        print("send_cart_reminder_emails completed successfully.")
    except Exception as e:
        print(f"Error in send_cart_reminder_emails: {str(e)}")
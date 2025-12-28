# E-commerce Platform – Detailed Setup & Usage Report

## Project Overview

This E-commerce platform is built with Django (Python) and MongoDB. It supports user registration, product browsing, cart management, order placement, checkout, coupon application, review moderation, refund requests, and an admin dashboard. The platform is designed for scalability, security, and a smooth user experience.

---

## 1. Prerequisites

- **Python 3.8+**
- **MongoDB** (local or Atlas cluster)
- **pip** (Python package manager)
- **Git** (for cloning the repository)

---

## 2. Clone the Repository

```sh
git clone https://github.com/Sugi04-cpu/Murugesan_Sugishivam_COMP_699_C
cd Murugesan_Sugishivam_COMP_699_C
```

---

## 3. Set Up a Virtual Environment

```sh
python -m venv env
# On Windows:
env\Scripts\activate
# On macOS/Linux:
source env/bin/activate
```

---

## 4. Install Dependencies

```sh
pip install -r requirements.txt
```

---

## 5. Configure MongoDB

- Ensure MongoDB is running locally (`mongodb://localhost:27017/`) or use a MongoDB Atlas URI.
- Update your Django settings or environment variables with your MongoDB connection string and database name, for example:
    ```python
    MONGO_URI = "mongodb://localhost:27017/"
    MONGO_DB_NAME = "e_commerce_db"
    ```
- No need to run `python manage.py migrate` as Django ORM is not used for MongoDB.

---

## 6. (Optional) Create a Superuser

If you want to use Django’s admin panel for other purposes:
```sh
python manage.py createsuperuser
```
> Note: The admin panel is not used for MongoDB data, but you can still use it for Django’s built-in apps.

---

## 7. Run the Development Server

```sh
python manage.py runserver
```
Visit [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your browser.

---

## 8. Features

### User Features
- **User Registration & Login:** Secure registration and authentication for users.
- **Profile Management:** Users can view their profile and manage saved addresses.
- **Product Browsing:** Browse products by category, view product details, and search for products.
- **Cart Management:** Add products to cart, update quantities, and remove items.
- **Checkout:** Place orders for items in the cart, select shipping address, and apply coupons.
- **Order Management:** View order history, order details, and track order status/timeline.
- **Order Tracking:** Real-time order status updates and timeline (Order Placed, Processed, Shipped, Delivered).
- **Review Submission:** Submit reviews for purchased products.
- **Refund Requests:** Request refunds for delivered orders.
- **Coupon Application:** Apply valid coupon codes at checkout for discounts.

### Admin Features
- **Admin Dashboard:** Access a dashboard to manage products, categories, users, orders, and coupons.
- **Product Management:** Add, edit, or delete products and categories.
- **Order Management:** View all orders, update order statuses (Pending, Shipped, Delivered, Cancelled).
- **Review Moderation:** Approve, reject, or delete product reviews.
- **Refund Requests:** View, approve, or reject refund requests from users.
- **Coupon Management:** Create, edit, or deactivate coupon codes.
- **User Management:** View user list and manage user roles.
- **Role-based Access:** Only admins can access moderation and refund management pages.

---

## 9. Sample Data

You can insert sample products, users, orders, reviews, coupons, and refund requests directly into MongoDB using the MongoDB shell or Compass for testing.

---

## 10. Troubleshooting

- **MongoDB Connection Errors:** Ensure MongoDB is running and the URI is correct.
- **Missing Dependencies:** Run `pip install -r requirements.txt` again.
- **Role-based Access:** Only admins can access moderation and refund management pages.

---

## 11. Project Structure

- `e_commerce/api/` – Django app logic, views, and MongoDB integration
    - `admin/` – Admin views (moderation, refund, product management)
    - `orders/` – Order and checkout logic
    - `cart/` – Cart management logic
    - `products/` – Product and category logic
    - `coupons/` – Coupon management logic
- `e_commerce/templates/` – HTML templates for users and admin
    - `admin/` – Admin dashboard and moderation templates
    - `users/` – User profile, cart, and order templates
    - `order_management/` – Order tracking and management
- `e_commerce/static/` – Static files (CSS, JS, images)
- `requirements.txt` – Python dependencies

---

## 12. Support

For questions or issues, contact [@Sugi004](https://github.com/Sugi004).

---

## 13. Credits

**Author:** Sugishivam Murugesan  
**GitHub:** [@Sugi004](https://github.com/Sugi004)

---

Give a ⭐️ if this project helped you!

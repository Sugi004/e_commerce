from ..mongoDb import get_collection
from datetime import datetime, timedelta
from bson import ObjectId

def initialize_cart_collection():
    """Initialize cart collection with required indexes"""
    cart_collection = get_collection("carts")
    
    # Create indexes
    cart_collection.create_index([("user_id", 1)], unique=True)
    cart_collection.create_index([("session_id", 1)], unique=True)
    cart_collection.create_index([("expires_at", 1)], expireAfterSeconds=0)
    
    return cart_collection

def get_user_cart(user_id=None, session_id=None):
    """Retrieve cart for user or session"""
    cart_collection = get_collection("carts")
    
    if user_id:
        return cart_collection.find_one({"user_id": str(user_id)})
    elif session_id:
        return cart_collection.find_one({"session_id": session_id})
    return None

def create_cart(user_id=None, session_id=None):
    """Create new cart document"""
    cart_collection = get_collection("carts")
    
    cart = {
        "items": [],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    if user_id:
        cart["user_id"] = str(user_id)
    elif session_id:
        cart["session_id"] = session_id
        cart["expires_at"] = datetime.utcnow() + timedelta(hours=24)
    
    result = cart_collection.insert_one(cart)
    return str(result.inserted_id)

def update_cart_item(cart_id, product_id, quantity, action="update"):
    """Update or remove cart items"""
    cart_collection = get_collection("carts")
    now = datetime.utcnow()
    
    if action == "remove":
        return cart_collection.update_one(
            {"_id": ObjectId(cart_id)},
            {
                "$pull": {"items": {"product_id": str(product_id)}},
                "$set": {"updated_at": now}
            }
        )
    
    # Check if item exists in cart
    cart = cart_collection.find_one({
        "_id": ObjectId(cart_id),
        "items.product_id": str(product_id)
    })
    
    if cart:
        # Update existing item
        return cart_collection.update_one(
            {
                "_id": ObjectId(cart_id),
                "items.product_id": str(product_id)
            },
            {
                "$set": {
                    "items.$.quantity": quantity,
                    "items.$.updated_at": now,
                    "updated_at": now
                }
            }
        )
    else:
        # Add new item
        return cart_collection.update_one(
            {"_id": ObjectId(cart_id)},
            {
                "$push": {
                    "items": {
                        "product_id": str(product_id),
                        "quantity": quantity,
                        "added_at": now,
                        "updated_at": now
                    }
                },
                "$set": {"updated_at": now}
            }
        )

def get_cart_items(cart_id):
    """Get all items in cart with product details"""
    cart_collection = get_collection("carts")
    product_collection = get_collection("products")
    
    cart = cart_collection.find_one({"_id": ObjectId(cart_id)})
    if not cart:
        return []
    
    cart_items = []
    for item in cart.get("items", []):
        product = product_collection.find_one({"_id": ObjectId(item["product_id"])})
        if product:
            product["_id"] = str(product["_id"])
            cart_items.append({
                "product": product,
                "quantity": item["quantity"],
                "added_at": item["added_at"],
                "updated_at": item["updated_at"],
                "subtotal": float(product.get("price", 0)) * item["quantity"]
            })

            
    
    return cart_items

def clear_cart(cart_id):
    """Remove all items from cart"""
    cart_collection = get_collection("carts")
    return cart_collection.update_one(
        {"_id": ObjectId(cart_id)},
        {
            "$set": {
                "items": [],
                "updated_at": datetime.utcnow()
            }
        }
    )
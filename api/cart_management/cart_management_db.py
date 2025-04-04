from ..mongoDb import get_collection
from datetime import datetime, timedelta
from bson import ObjectId

def initialize_cart_collection():
 
    cart_collection = get_collection("carts")
    
    # Create indexes
    cart_collection.create_index([("user_id", 1)], unique=True)
    cart_collection.create_index([("session_id", 1)], unique=True)
    cart_collection.create_index([("expires_at", 1)], expireAfterSeconds=0)
    
    return cart_collection

def get_user_cart(user_id=None, session_id=None):
    cart_collection = get_collection("carts")
    try:
        if user_id:
            return cart_collection.find_one({"user_id": str(user_id)})
        elif session_id:
            return cart_collection.find_one({"session_id": session_id})
    except Exception as e:
        print(f"Error getting cart: {str(e)}")
        return None
   
    return None

def create_cart(user_id=None, session_id=None):
    """Create new cart document"""
    cart_collection = get_collection("carts")
    now = datetime.utcnow()
    
    cart = {
        "items": [],
        "created_at": now,
        "updated_at": now
    }
    
    # Add identifiers based on what's provided
    if user_id:
        cart["user_id"] = str(user_id)
        # User carts don't expire
    
    if session_id:
        cart["session_id"] = session_id
        cart["expires_at"] = now + timedelta(hours=24)
    
    try:
        result = cart_collection.insert_one(cart)
        return str(result.inserted_id)
    except Exception as e:
        print(f"Error creating cart: {str(e)}")
        return None

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

def transfer_guest_cart(session_id, user_id):
    """Transfer items from guest cart to user cart"""
    cart_collection = get_collection("carts")
    
    # Get guest cart
    guest_cart = cart_collection.find_one({"session_id": session_id})
    if not guest_cart:
        return None
        
    # Get or create user cart
    user_cart = cart_collection.find_one({"user_id": str(user_id)})
    if not user_cart:
        create_cart(user_id=user_id)
        user_cart = cart_collection.find_one({"user_id": str(user_id)})
    
    # Transfer items
    if guest_cart.get("items"):
        now = datetime.utcnow()
        # Update user cart with guest items
        cart_collection.update_one(
            {"_id": user_cart["_id"]},
            {
                "$push": {
                    "items": {
                        "$each": guest_cart["items"]
                    }
                },
                "$set": {
                    "updated_at": now
                }
            }
        )
        
        # Remove guest cart
        cart_collection.delete_one({"_id": guest_cart["_id"]})
        
    return user_cart["_id"]
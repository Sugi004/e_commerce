from ..modules import *
from .cart_schema import CartSchema
from ..utils.date_utils import validate_and_convert_dates

def initialize_carts_collection():
    
    # Create indexes
    carts_collection.create_index([("user_id", 1)], unique=True)
    carts_collection.create_index([("session_id", 1)], unique=True)
    carts_collection.create_index([("expires_at", 1)], expireAfterSeconds=0)
    
    return carts_collection

def get_user_cart(user_id=None, session_id=None):
    try:
        if user_id:
            return carts_collection.find_one({"user_id": str(user_id)})
        elif session_id:
            return carts_collection.find_one({"session_id": session_id})
    except Exception as e:
        print(f"Error getting cart: {str(e)}")
        return None
   
    return None

def create_cart(user_id=None, session_id=None):
    """Create new cart document"""
    now = datetime.utcnow()
    
    cart = {
        "items": [],
        "created_at": now,
        "updated_at": now,
    }
    
    # Add identifiers based on what's provided
    if user_id:
        cart["user_id"] = str(user_id)
        # User carts don't expire
    
    if session_id:
        cart["session_id"] = session_id
        cart["expires_at"] = now + timedelta(hours=24)
    
    

    cart_schema = CartSchema()

    validated_cart = validate_and_convert_dates(cart, ["created_at", "updated_at", "expires_at"])

    try:
        cart_schema.load(validated_cart)  # Validate the cart schema
    except ValidationError as e:
        print(f"Cart validation error: {e.messages}")
        return None

    try:
        result = carts_collection.insert_one(cart)
        return str(result.inserted_id)
    except Exception as e:
        print(f"Error creating cart: {str(e)}")
        return None

def update_cart_item(cart_id, product_id, quantity, action="update"):
    """Update or remove cart items"""
    now = datetime.utcnow()
    
    if action == "remove":
        return carts_collection.update_one(
            {"_id": ObjectId(cart_id)},
            {
                "$pull": {"items": {"product_id": str(product_id)}},
                "$set": {"updated_at": now}
            }
        )
    
    # Check if item exists in cart
    cart = carts_collection.find_one({
        "_id": ObjectId(cart_id),
        "items.product_id": str(product_id)
    })
    
    if cart:
        # Update existing item
        return carts_collection.update_one(
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
        return carts_collection.update_one(
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
    cart = carts_collection.find_one({"_id": ObjectId(cart_id)})
    if not cart:
        return []
    
    cart_items = []
    for item in cart.get("items", []):
        product = products_collection.find_one({"_id": ObjectId(item["product_id"])})
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
    carts_collection = get_collection("carts")
    return carts_collection.update_one(
        {"_id": ObjectId(cart_id)},
        {
            "$set": {
                "items": [],
                "updated_at": datetime.utcnow()
            }
        }
    )

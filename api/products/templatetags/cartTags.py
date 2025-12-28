from django import template
from ...mongoDb import get_collection
from bson import ObjectId

register = template.Library()

@register.simple_tag(takes_context=True)
def get_cart_count(context):
    request = context['request']
    cart_count = 0
    user_id = request.session.get('user_id')
    if user_id:
        carts_collection = get_collection("carts")
        cart = carts_collection.find_one({"user_id": ObjectId(user_id)})
        if cart and "items" in cart:
            cart_count = len(cart["items"])
    return cart_count
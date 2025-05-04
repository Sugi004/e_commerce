from marshmallow import Schema, fields, validates, ValidationError
from bson import ObjectId

# Custom ObjectId field for MongoDB validation
class ObjectIdField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        return str(value) if isinstance(value, ObjectId) else None

    def _deserialize(self, value, attr, data, **kwargs):
        try:
            return ObjectId(value)
        except:
            raise ValidationError("Invalid ObjectId format")

# Order Item Schema
class OrderItemSchema(Schema):
    product_id = ObjectIdField(required=True)  # Reference to the product's _id
    quantity = fields.Int(required=True, validate=lambda x: x > 0)  # Must be greater than 0
    price = fields.Float(required=True)  # Price of the product at the time of order

# Order Schema
class OrderSchema(Schema):
    _id = ObjectIdField(required=False)  # MongoDB automatically generates ObjectId
    user_id = ObjectIdField(required=True)  # Reference to the user's _id
    items = fields.List(fields.Nested(OrderItemSchema), required=True)  # List of ordered items
    total_price = fields.Float(required=True)  # Total price of the order
    status = fields.Str(
        required=True,
        validate=lambda x: x in ["Pending", "Shipped", "Delivered", "Cancelled"]
    )  # Order status
    created_at = fields.DateTime(required=False)  # Timestamp when the order was created
    updated_at = fields.DateTime(required=False)  # Timestamp when the order was last updated

    @validates("total_price")
    def validate_total_price(self, value):
        if value <= 0:
            raise ValidationError("Total price must be greater than 0.")

# Refund Request Schema
class RefundRequestSchema(Schema):
    _id = ObjectIdField(required=False)
    order_id = ObjectIdField(required=True)  # Reference to the order's _id
    user_id = ObjectIdField(required=True)  # Reference to the user's _id
    reason = fields.Str(required=True)  # Reason for the refund request
    status = fields.Str(
        required=True,
        validate=lambda x: x in ["Pending", "Approved", "Rejected"]
    )  # Refund request status
    amount = fields.Float(required=True)  # Amount to be refunded
    requested_at = fields.DateTime(required=False)  # Timestamp when the refund was requested
    updated_at = fields.DateTime(required=False)  # Timestamp when the refund status was last updated


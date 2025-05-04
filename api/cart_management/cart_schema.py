from ..modules import ValidationError, ObjectId, fields, Schema, validates, datetime, timedelta

# Custom ObjectId field for MongoDB validation
class ObjectIdField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        return str(value) if isinstance(value, ObjectId) else None

    def _deserialize(self, value, attr, data, **kwargs):
        try:
            return ObjectId(value)
        except:
            raise ValidationError("Invalid ObjectId format")

# Cart Schema
class CartSchema(Schema):
    _id = ObjectIdField(required=False)
    session_id = fields.Str(required=False)
    user_id = ObjectIdField(required=False, allow_none=True)
    items = fields.List(fields.Dict(), missing=[])
    created_at = fields.DateTime(required=False, missing=datetime.utcnow)
    updated_at = fields.DateTime(required=False, missing=datetime.utcnow)
    expires_at = fields.DateTime(required=False, missing=lambda: datetime.utcnow() + timedelta(hours=24))

# Coupons Schema
class CouponSchema(Schema):
    _id = ObjectIdField(required=False)
    code = fields.Str(required=True, validate=lambda x: 3 <= len(x) <= 20)
    discount = fields.Float(required=True, validate=lambda x: x > 0 or ValidationError("Discount must be greater than 0"))
    expiry_date = fields.DateTime(required=True)
    max_uses = fields.Int(required=False, validate=lambda x: x > 0 if x is not None else True)
    used_count = fields.Int(missing=0)
    is_active = fields.Bool(missing=True)
    created_at = fields.DateTime(missing=datetime.utcnow)
    updated_at = fields.DateTime(missing=datetime.utcnow)

    @validates("expiry_date")
    def validate_expiry_date(self, value):
        if value <= datetime.utcnow():
            raise ValidationError("Expiry date must be in the future.")
    
    @validates("discount")
    def validate_discount(self, value):
        if value <= 0:
            raise ValidationError("Discount must be greater than 0.")
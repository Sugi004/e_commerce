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

# Address Schema (Only for Customers)
class AddressSchema(Schema):
    type = fields.Str(required=True)
    street = fields.Str(required=True)
    city = fields.Str(required=True)
    state = fields.Str(required=True)
    zip = fields.Str(required=True)
    country = fields.Str(required=True)

# User Schema
class UserSchema(Schema):
    _id = ObjectIdField(required=False)  # MongoDB automatically generates ObjectId
    name = fields.Str(required=True)
    email = fields.Email(required=True)
    password = fields.Str(required=True, load_only=True)  # Never return password
    phone = fields.Str(required=True)
    role = fields.Str(required=True, validate=lambda x: x in ["admin", "customer", "guest"])
    is_active = fields.Bool(default=True)
    is_locked = fields.Bool(default=False)
    created_at = fields.DateTime(required=False)
    updated_at = fields.DateTime(required=False)
    addresses = fields.List(fields.Nested(AddressSchema), required=False)
    #Only for admin users
    permissions = fields.Dict(
        keys=fields.Str(),
        values=fields.Bool(),
        required=False
    )

    @validates("role")
    def validate_role(self, value):
        if value.lower() not in ["admin", "customer", "guest"]:
            raise ValidationError("Invalid role. Must be 'admin', 'customer', or 'guest'.")

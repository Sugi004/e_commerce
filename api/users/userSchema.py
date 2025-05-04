from ..modules import validate, ObjectId, fields, Schema, validates, ValidationError

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
    user_id = ObjectIdField(required=True)  # Reference to the user's _id in the users collection
    type = fields.Str(required=True)
    street = fields.Str(required=True)
    city = fields.Str(required=True)
    state = fields.Str(required=True)
    zip = fields.Str(required=True)
    country = fields.Str(required=True)
    phone = fields.Str(required=False)

# User Schema
class UserSchema(Schema):
    _id = ObjectIdField(required=False)  # MongoDB automatically generates ObjectId
    name = fields.Str(required=True)
    email = fields.Email(required=True)
    password = fields.Str(required=True, load_only=True)  # Never return password
    role = fields.Str(required=False, missing="customer")
    is_active = fields.Bool(default=True, missing=True)
    is_locked = fields.Bool(default=False, missing=False)
    created_at = fields.DateTime(required=False)
    updated_at = fields.DateTime(required=False)
    addresses = fields.List(fields.Nested(AddressSchema), required=False)
    #Only for admin users
    permissions = fields.Dict(
        keys=fields.Str(),
        values=fields.Bool(),
        required=False
    )
    failed_attempts = fields.Int(default=0, missing=0) 
    last_failed_attempt = fields.DateTime(required=False)
    reset_token = fields.Str(required=False)
    reset_token_expires = fields.DateTime(required=False)

    @validates("role")
    def validate_role(self, value):
        if value.lower() == "admin" and not self.context.get("is_admin", False):
            raise ValidationError("Only admins can assign the role 'admin'.")

from ..modules import Schema, fields, ValidationError, validates, validate, ObjectId




# Custom field for ObjectId validation
class ObjectIdField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        if not isinstance(value, ObjectId):
            raise ValidationError("Invalid ObjectId")
        return str(value)

    def _deserialize(self, value, attr, data, **kwargs):
        try:
            return ObjectId(value)
        except Exception:
            raise ValidationError("Invalid ObjectId")


# Define Product Schema dynamically
ProductSchema = Schema.from_dict({
    "_id": ObjectIdField(required=False, allow_none=True),
    "name": fields.Str(required=True),
    "price": fields.Float(required=True, validate=lambda x: x >= 0),  # Price must be >= 0
    "category": fields.Str(required=True),
    "description": fields.Str(required=False),
    "stock": fields.Int(required=True, validate=lambda x: x >= 0),  # Stock must be >= 0
    "seller_id": fields.Raw(required=True, allow_none=True),
    "discount_percentage": fields.Int(required=False, default=0, validate=validate.Range(min=0, max=100)),
    "is_active": fields.Bool(required=False, default=True),                 # Hide inactive products
    "tags": fields.List(fields.Str(), required=False),                      # Tags for filtering
    "attributes": fields.Dict(
        required=True,
        keys=fields.Str(),
        values=fields.Raw(),
        description="A flexible dictionary for product-specific attributes"
    ),
    "image_url": fields.Url(),
    "availability": fields.Str(required=False, default=True),
})

# Individual Review Schema
class IndividualReviewSchema(Schema):
    id = ObjectIdField(required=True)  # Unique ID for the review
    user_id = fields.Str(required=True)  # Session key or user ID
    rating = fields.Int(required=True, validate=lambda x: 1 <= x <= 5)  # Rating between 1 and 5
    status = fields.Str(required=True, validate=lambda x: x in ["pending", "approved", "rejected"])  # Review status
    review = fields.Str(required=True)  # Review text
    created_at = fields.DateTime(required=True)  # Timestamp when the review was created
    updated_at = fields.DateTime(required=True)  # Timestamp when the review was last updated

    @validates("rating")
    def validate_rating(self, value):
        if not (1 <= value <= 5):
            raise ValidationError("Rating must be between 1 and 5.")

    @validates("status")
    def validate_status(self, value):
        if value not in ["pending", "approved", "rejected"]:
            raise ValidationError("Invalid status. Must be one of ['pending', 'approved', 'rejected'].")


# Review Schema
class ReviewSchema(Schema):
    _id = ObjectIdField(required=False)
    product_id = ObjectIdField(required=True)  # Reference to the product's _id
    reviews = fields.List(fields.Nested(IndividualReviewSchema), required=True)  # Array of reviews

    @validates("reviews")
    def validate_reviews(self, value):
        if not value or not isinstance(value, list):
            raise ValidationError("Reviews must be a non-empty list of valid review objects.")



from marshmallow import Schema, fields

# PUBLIC_INTERFACE
class UserProfileSchema(Schema):
    id = fields.Int()
    email = fields.Str()
    name = fields.Str()
    profile_pic = fields.Str(required=False)
    preferences = fields.Nested(lambda: UserPreferenceSchema())

# PUBLIC_INTERFACE
class UserPreferenceSchema(Schema):
    reading_level = fields.Str()
    summary_detail = fields.Str()
    preferred_topics = fields.Str()

# PUBLIC_INTERFACE
class SummarySchema(Schema):
    id = fields.Int()
    source_type = fields.Str()
    input_title = fields.Str()
    summary_text = fields.Str()
    created_at = fields.DateTime()

# PUBLIC_INTERFACE
class BookmarkSchema(Schema):
    id = fields.Int()
    summary = fields.Nested(SummarySchema)
    created_at = fields.DateTime()

# PUBLIC_INTERFACE
class CreateSummaryRequest(Schema):
    source_type = fields.Str(required=True, description="url|text|news")
    source_value = fields.Str(required=True, description="URL, raw text, or news ID")
    input_title = fields.Str(description="title, for 'text' option")

# PUBLIC_INTERFACE
class PreferenceUpdateSchema(Schema):
    reading_level = fields.Str(required=False)
    summary_detail = fields.Str(required=False)
    preferred_topics = fields.Str(required=False)


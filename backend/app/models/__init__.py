"""ORM models. Importing this package registers every table on Base.metadata."""
from app.models.api_key import ApiKey
from app.models.background import Background
from app.models.domain import CustomDomain
from app.models.page import Icon, Link, Page, Section, SocialLink
from app.models.user import User

__all__ = [
    "ApiKey",
    "Background",
    "CustomDomain",
    "Icon",
    "Link",
    "Page",
    "Section",
    "SocialLink",
    "User",
]

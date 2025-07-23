import os
import requests
from functools import wraps
from flask import jsonify, session

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
GOOGLE_DISCOVERY_URL = (
    "https://accounts.google.com/.well-known/openid-configuration"
)
REDIRECT_URI = os.environ.get("GOOGLE_OAUTH_REDIRECT", "http://localhost:3001/api/auth/callback")

def get_google_provider_cfg():
    return requests.get(GOOGLE_DISCOVERY_URL).json()

# PUBLIC_INTERFACE
def login_required(fn):
    """Decorator to enforce OAuth-based authentication for protected routes."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return jsonify({"error": "Authentication required"}), 401
        return fn(*args, **kwargs)
    return wrapper

# PUBLIC_INTERFACE
def get_current_user():
    """Return the current user info from session (if available)."""
    user = session.get("user")
    if not user:
        return None
    return user


import os
from flask import Flask
from flask_cors import CORS
from flask_smorest import Api
from .routes.health import blp as health_blp
from .routes.api import blp as api_blp
from .models import db

def get_database_uri():
    """Get DB URI from env variables for Postgres/MySQL/SQLite connection."""
    db_url = os.environ.get("SQLALCHEMY_DATABASE_URI")
    if db_url:
        return db_url
    # Expected: Use env vars for user/pass/host/db name for 'bitesize_database'
    # Example with Postgres:
    POSTGRES_USER = os.environ.get("POSTGRES_USER")
    POSTGRES_PW = os.environ.get("POSTGRES_PASSWORD")
    POSTGRES_HOST = os.environ.get("POSTGRES_HOST")
    POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")
    POSTGRES_DB = os.environ.get("POSTGRES_DB", "bitesize_database")
    if POSTGRES_USER and POSTGRES_PW and POSTGRES_HOST:
        return f"postgresql://{POSTGRES_USER}:{POSTGRES_PW}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    # fallback
    return "sqlite:///bitesize.db"

app = Flask(__name__)
app.url_map.strict_slashes = False
CORS(app, resources={r"/*": {"origins": "*"}})
app.config["API_TITLE"] = "BiteSize API"
app.config["API_VERSION"] = "v1"
app.config["OPENAPI_VERSION"] = "3.0.3"
app.config['OPENAPI_URL_PREFIX'] = '/docs'
app.config["OPENAPI_SWAGGER_UI_PATH"] = ""
app.config["OPENAPI_SWAGGER_UI_URL"] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"
app.secret_key = os.environ.get("SECRET_KEY", "bitesize-SECRET")

app.config['SQLALCHEMY_DATABASE_URI'] = get_database_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

api = Api(app)
api.register_blueprint(health_blp)
api.register_blueprint(api_blp)

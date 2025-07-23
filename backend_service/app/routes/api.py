import os
from flask import request, session, redirect
from flask.views import MethodView
from flask_smorest import Blueprint as SmorestBlueprint
from app.auth import login_required, get_current_user, get_google_provider_cfg
from app.models import db, User, Summary, Bookmark, UserPreference
from app.schemas import (
    UserProfileSchema, UserPreferenceSchema, SummarySchema, BookmarkSchema,
    CreateSummaryRequest, PreferenceUpdateSchema
)
from app.services import (
    fetch_url_content, summarize_text_ai, get_news_articles,
)
import requests
from urllib.parse import urlencode

blp = SmorestBlueprint(
    "API", "api", url_prefix="/api", description="Main API for BiteSize backend"
)

# --- AUTH ENDPOINTS ---

@blp.route('/auth/login')
class GoogleOAuthLogin(MethodView):
    """
    PUBLIC_INTERFACE
    Initiate Google OAuth2 login, redirect user to Google's authorization page.
    """
    def get(self):
        google_cfg = get_google_provider_cfg()
        auth_endpoint = google_cfg["authorization_endpoint"]
        redirect_uri = os.environ.get("GOOGLE_OAUTH_REDIRECT", "http://localhost:3001/api/auth/callback")
        params = {
            "client_id": os.environ["GOOGLE_CLIENT_ID"],
            "redirect_uri": redirect_uri,
            "scope": "openid email profile",
            "response_type": "code",
            "prompt": "select_account"
        }
        return redirect(auth_endpoint + "?" + urlencode(params))

@blp.route('/auth/callback')
class GoogleOAuthCallback(MethodView):
    """
    PUBLIC_INTERFACE
    Handle Google OAuth2 callback, exchange code for token, and log user in.
    """
    def get(self):
        code = request.args.get("code")
        if not code:
            return {"error":"Missing code param"}, 400
        google_cfg = get_google_provider_cfg()
        token_endpoint = google_cfg["token_endpoint"]
        token_data = {
            "code": code,
            "client_id": os.environ["GOOGLE_CLIENT_ID"],
            "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
            "redirect_uri": os.environ.get("GOOGLE_OAUTH_REDIRECT", "http://localhost:3001/api/auth/callback"),
            "grant_type": "authorization_code"
        }
        token_response = requests.post(token_endpoint, data=token_data)
        token_response.raise_for_status()
        tokens = token_response.json()
        userinfo_endpoint = google_cfg["userinfo_endpoint"]
        userinfo_response = requests.get(
            userinfo_endpoint,
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        userinfo = userinfo_response.json()
        email = userinfo["email"]
        oauth_sub = userinfo["sub"]
        # Find or create user
        user = User.query.filter_by(oauth_sub=oauth_sub).first()
        if user is None:
            user = User(
                oauth_sub=oauth_sub,
                email=email,
                name=userinfo.get("name"),
                profile_pic=userinfo.get("picture")
            )
            db.session.add(user)
            db.session.commit()
        session['user'] = {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "profile_pic": user.profile_pic,
        }
        return redirect(os.environ.get("LOGIN_SUCCESS_REDIRECT_URL", "/"))

@blp.route('/auth/logout')
class Logout(MethodView):
    """
    PUBLIC_INTERFACE
    OAuth-protected, logs out user.
    """
    @login_required
    def post(self):
        session.pop("user", None)
        return {"message": "Logged out"}

@blp.route('/auth/user')
class AuthProfile(MethodView):
    """
    PUBLIC_INTERFACE
    Return details about the current user.
    """
    @login_required
    @blp.response(200, UserProfileSchema)
    def get(self):
        user_obj = User.query.get(get_current_user()["id"])
        prefs = user_obj.preferences
        return {
            "id": user_obj.id,
            "email": user_obj.email,
            "name": user_obj.name,
            "profile_pic": user_obj.profile_pic,
            "preferences": prefs,
        }

# --- USER PREFS ---

@blp.route("/user/preferences")
class UserPreferences(MethodView):
    """
    PUBLIC_INTERFACE
    View or update user's summary preferences.
    """
    @login_required
    @blp.response(200, UserPreferenceSchema)
    def get(self):
        user_obj = User.query.get(get_current_user()["id"])
        prefs = user_obj.preferences
        if not prefs:
            # Defaults
            prefs = UserPreference(
                user_id=user_obj.id,
                reading_level="general",
                summary_detail="brief",
                preferred_topics=""
            )
            db.session.add(prefs)
            db.session.commit()
        return prefs

    @login_required
    @blp.arguments(PreferenceUpdateSchema)
    @blp.response(200, UserPreferenceSchema)
    def put(self, prefs_data):
        user_obj = User.query.get(get_current_user()["id"])
        prefs = user_obj.preferences
        if not prefs:
            prefs = UserPreference(user_id=user_obj.id)
            db.session.add(prefs)
        if "reading_level" in prefs_data:
            prefs.reading_level = prefs_data["reading_level"]
        if "summary_detail" in prefs_data:
            prefs.summary_detail = prefs_data["summary_detail"]
        if "preferred_topics" in prefs_data:
            prefs.preferred_topics = prefs_data["preferred_topics"]
        db.session.commit()
        return prefs

# --- SUMMARY CREATION & VIEW ---

@blp.route('/summaries')
class Summaries(MethodView):
    """
    PUBLIC_INTERFACE
    Submit article URLs/text, AI summarization, and view summaries (paginated).
    """
    @login_required
    @blp.arguments(CreateSummaryRequest)
    @blp.response(200, SummarySchema)
    def post(self, req):
        cur_user = User.query.get(get_current_user()["id"])
        prefs = cur_user.preferences
        source_type = req["source_type"]
        source_value = req["source_value"]
        input_title = req.get("input_title") or ""
        if source_type == "url":
            title, page_content = fetch_url_content(source_value)
            if not page_content:
                return {"error": "Could not fetch or read the provided URL."}, 400
            summary_text = summarize_text_ai(page_content, cur_user, prefs)
        elif source_type == "text":
            page_content = source_value
            title = input_title if input_title else "Custom Text"
            summary_text = summarize_text_ai(page_content, cur_user, prefs)
        elif source_type == "news":
            # news source_value is news-article id, fetch the article from db or API
            news_id = source_value
            articles = get_news_articles(query=news_id)
            if not articles or not articles.get("articles"):
                return {"error": "Could not fetch news article."}, 400
            article = articles["articles"][0]
            text = article.get("content", "") or article.get("description", "")
            title = article.get("title", "News Article")
            summary_text = summarize_text_ai(text, cur_user, prefs)
        else:
            return {"error": "Invalid source type"}, 400

        summary = Summary(
            user_id=cur_user.id,
            source_type=source_type,
            source_value=source_value,
            input_title=title,
            summary_text=summary_text,
        )
        db.session.add(summary)
        db.session.commit()
        return summary

    @login_required
    @blp.response(200, SummarySchema(many=True))
    def get(self):
        """
        Fetch summaries created by user (paginated and most recent first).
        """
        cur_user = User.query.get(get_current_user()["id"])
        page = int(request.args.get("page", 1))
        summaries = (
            Summary.query.filter_by(user_id=cur_user.id)
            .order_by(Summary.created_at.desc())
            .paginate(page=page, per_page=10, error_out=False)
        )
        return summaries.items

# --- BOOKMARKS ---

@blp.route('/bookmarks')
class BookmarkList(MethodView):
    """
    PUBLIC_INTERFACE
    View or add bookmarks.
    """
    @login_required
    @blp.response(200, BookmarkSchema(many=True))
    def get(self):
        cur_user = User.query.get(get_current_user()["id"])
        bms = Bookmark.query.filter_by(user_id=cur_user.id).order_by(Bookmark.created_at.desc()).all()
        return bms

    @login_required
    def post(self):
        data = request.json
        sum_id = data.get("summary_id")
        cur_user = User.query.get(get_current_user()["id"])
        summary = Summary.query.get(sum_id)
        if not summary:
            return {"error": "Not found"}, 404
        if Bookmark.query.filter_by(user_id=cur_user.id, summary_id=sum_id).first():
            return {"error": "Already bookmarked"}, 409
        bm = Bookmark(user_id=cur_user.id, summary_id=sum_id)
        db.session.add(bm)
        db.session.commit()
        return {"message": "Bookmarked", "id": bm.id}

@blp.route('/bookmarks/<int:bm_id>')
class BookmarkDelete(MethodView):
    """
    PUBLIC_INTERFACE
    Delete a bookmark.
    """
    @login_required
    def delete(self, bm_id):
        cur_user = User.query.get(get_current_user()["id"])
        bm = Bookmark.query.filter_by(user_id=cur_user.id, id=bm_id).first()
        if not bm:
            return {"error": "Not found"}, 404
        db.session.delete(bm)
        db.session.commit()
        return {"message": "Deleted"}

# --- NEWS API BROWSE ---

@blp.route('/news')
class NewsSearch(MethodView):
    """
    PUBLIC_INTERFACE
    Fetch news headlines/articles (browsing/discovery).
    """
    @login_required
    def get(self):
        query = request.args.get("query")
        page = int(request.args.get("page", 1))
        res = get_news_articles(query=query, page=page)
        return res


import os
import requests
from openai import OpenAI
from bs4 import BeautifulSoup

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")

client = None

if OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY)

# PUBLIC_INTERFACE
def fetch_url_content(url):
    """Retrieve and clean content from a given URL for summarization."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, features="html.parser")
        # Get text from paragraphs
        paragraphs = soup.find_all('p')
        text = " ".join([p.get_text() for p in paragraphs])
        # Fallback: Use body text
        if not text.strip():
            text = soup.body.get_text()
        title = soup.title.string if soup.title else url
        return title, text.strip()
    except Exception:
        return None, None

# PUBLIC_INTERFACE
def summarize_text_ai(text, user, preferences=None):
    """Send the article/text to OpenAI and get summary tailored to user's settings."""
    user_name = user.name if user else "user"
    prompt = f"You are a helpful summarizer for articles. Summarize this in less than 100 words as concise bullet points for {user_name}."
    if preferences:
        if preferences.reading_level:
            prompt += f" Target a {preferences.reading_level} reading level."
        if preferences.summary_detail:
            prompt += f" Focus on {preferences.summary_detail} detail."
        if preferences.preferred_topics:
            prompt += f" Pay special attention to topics: {preferences.preferred_topics}."
    prompt += f"\nContent:\n{text}\nSummary:"

    if not client:
        raise RuntimeError("OpenAI client not configured.")
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "You are a concise, accurate article summarization AI assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=300,
        temperature=0.6,
    )
    ans = response.choices[0].message.content.strip()
    return ans

# PUBLIC_INTERFACE
def get_news_articles(query=None, page=1):
    """Fetch news articles using News API."""
    if not NEWS_API_KEY:
        raise ValueError("NEWS_API_KEY not set.")
    params = {
        "apiKey": NEWS_API_KEY,
        "sortBy": "publishedAt",
        "language": "en",
        "pageSize": 10,
        "page": page
    }
    if query:
        params["q"] = query
    resp = requests.get("https://newsapi.org/v2/top-headlines" if not query
                        else "https://newsapi.org/v2/everything", params=params)
    return resp.json()


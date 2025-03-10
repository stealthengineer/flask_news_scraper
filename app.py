from flask import Flask, jsonify, render_template
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from flask_cors import CORS
import requests
import os
import random
import time  # Caching
import praw
import tweepy
import time


from dotenv import load_dotenv

app = Flask(__name__, template_folder="templates")
CORS(app)

load_dotenv()
NEWS_API_KEY = os.getenv("NEWS_API_KEY")  # Secure API key

STOCKS_TO_TRACK = [
    "META", "AMZN", "AAPL", "NFLX", "GOOGL",
    "NVDA", "MSFT", "TSLA",
    "SPY", "QQQ", "DIA"
]

async def fetch_finviz_page(session, ticker):
    url = f"https://finviz.com/quote.ashx?t={ticker}"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/"
    }
    async with session.get(url, headers=headers) as response:
        return await response.text(), ticker, url

async def scrape_finviz():
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_finviz_page(session, ticker) for ticker in STOCKS_TO_TRACK]
        responses = await asyncio.gather(*tasks)

    stock_data = []
    for html, ticker, url in responses:
        soup = BeautifulSoup(html, "html.parser")
        price_element = soup.find("strong", class_="quote-price_wrapper_price")
        stock_price = price_element.text.strip() if price_element else "N/A"
        stock_data.append({"ticker": ticker, "price": stock_price, "link": url})

    return stock_data

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/scrape', methods=['GET'])
async def scrape():
    data = await scrape_finviz()
    return jsonify(data)

cached_news = {"data": [], "timestamp": 0}

def fetch_news():
    """Fetch latest news headlines with caching"""
    global cached_news
    CACHE_DURATION = 300  # Cache for 5 minutes

    if time.time() - cached_news["timestamp"] < CACHE_DURATION:
        return cached_news["data"]

    url = f"https://newsapi.org/v2/top-headlines?category=business&language=en&apiKey=0dda9ba8ed384629877f8307d6344a7b"
    response = requests.get(url)

    if response.status_code != 200:
        return [{"title": "Error fetching news", "link": "#"}]

    data = response.json()
    articles = data.get("articles", [])  # Prevent missing key errors

    synthetic_news = []
    for article in articles:
        title = article.get("title", "No Title")
        variation = random.choice([
            f"🚀 {title} - Breaking Now!",
            f"🔥 Urgent: {title}",
            f"📢 {title} - What You Need to Know",
            f"🔍 Analysis: {title}",
            f"📡 Live Update: {title}"
        ])
        synthetic_news.append({"title": variation, "link": article.get("url", "#")})

    cached_news["data"] = synthetic_news
    cached_news["timestamp"] = time.time()
    return synthetic_news

@app.route('/news')
def get_news():
    return jsonify(fetch_news())


# Reddit API Credentials
reddit = praw.Reddit(
    client_id="GSr-OBjCVO8w1iNh5qyYSg",
    client_secret="PypDovq6mYkhOKNJCWRCaQNwdb6Kdw",
    user_agent="Charming-Designer229"
)

def fetch_reddit_trending():
    """Fetch trending Reddit posts from r/StockMarket and r/Finance."""
    trending_posts = []
    subreddits = ["StockMarket", "Finance"]

    for sub in subreddits:
        subreddit = reddit.subreddit(sub)
        for post in subreddit.hot(limit=5):  # Get top 5 trending posts
            trending_posts.append({"title": post.title, "link": post.url})

    return trending_posts

@app.route('/reddit')
def get_reddit():
    return jsonify(fetch_reddit_trending())

TWITTER_BEARER_TOKEN = "AAAAAAAAAAAAAAAAAAAAAItbzwEAAAAAugnWGwrIg7WOtsGt9MO8yNxnT7Q%3DoC7mhxQaCdD98lEz1WodDXBQJXrMU0GAto3eyI8itmrL8hZPgw"

client = tweepy.Client(bearer_token=TWITTER_BEARER_TOKEN, wait_on_rate_limit=True)

cached_twitter = {"data": [], "timestamp": 0}

def fetch_twitter_trending():
    """Fetch trending tweets about stocks and finance with caching."""
    global cached_twitter
    CACHE_DURATION = 300  # Cache for 5 minutes (300 seconds)

    # Check if cache is still valid
    if time.time() - cached_twitter["timestamp"] < CACHE_DURATION and cached_twitter["data"]:
        print("Returning cached Twitter data")
        return cached_twitter["data"]

    # If cache is expired or empty, fetch new data
    trending_tweets = []
    query = "stocks OR finance OR economy -is:retweet lang:en"

    try:
        tweets = client.search_recent_tweets(query=query, max_results=10, tweet_fields=["text"])
        if not tweets.data:
            cached_twitter["data"] = [{"title": "No recent trending tweets found"}]
        else:
            for tweet in tweets.data:
                trending_tweets.append({"title": tweet.text})
            cached_twitter["data"] = trending_tweets
    except tweepy.TweepyException as e:
        print(f"Twitter API error: {e}")
        cached_twitter["data"] = [{"title": f"Error fetching tweets: {str(e)}"}]
    except Exception as e:
        print(f"Unexpected error: {e}")
        cached_twitter["data"] = [{"title": "Unexpected error fetching tweets"}]

    # Update the timestamp when new data is fetched
    cached_twitter["timestamp"] = time.time()
    print("Fetched new Twitter data and updated cache")
    return cached_twitter["data"]

@app.route('/twitter')
def get_twitter():
    return jsonify(fetch_twitter_trending())

if __name__ == "__main__":
    app.run(debug=True)


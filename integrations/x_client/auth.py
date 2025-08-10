import os
import tweepy
from dotenv import load_dotenv

load_dotenv()

# These should be set in your .env file
API_KEY = os.getenv("X_API_KEY")
API_SECRET = os.getenv("X_API_SECRET")
CALLBACK_URL = "http://localhost:8000/x/callback"  # or your prod URL

def get_auth_url():
    auth = tweepy.OAuth1UserHandler(API_KEY, API_SECRET, CALLBACK_URL)
    redirect_url = auth.get_authorization_url()
    return redirect_url, auth.request_token  # Save this token to match on callback

def get_user_api(oauth_token, oauth_verifier, saved_request_token):
    auth = tweepy.OAuth1UserHandler(API_KEY, API_SECRET)
    auth.request_token = saved_request_token
    auth.get_access_token(oauth_verifier)
    return tweepy.API(auth)
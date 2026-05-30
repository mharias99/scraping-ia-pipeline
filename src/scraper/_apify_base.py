"""Base compartida para todos los scrapers que usan Apify."""
import os
from apify_client import ApifyClient


def get_apify_client() -> ApifyClient:
    token = os.getenv("APIFY_API_TOKEN")
    if not token:
        raise EnvironmentError("APIFY_API_TOKEN no definida en .env")
    return ApifyClient(token)

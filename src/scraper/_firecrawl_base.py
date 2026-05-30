"""Cliente Firecrawl compartido para web_inspector y cualquier módulo que lo necesite."""
import os
from firecrawl import V1FirecrawlApp


def get_firecrawl_client() -> V1FirecrawlApp:
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "FIRECRAWL_API_KEY no definida en .env\n"
            "Obtén una key en https://www.firecrawl.dev"
        )
    return V1FirecrawlApp(api_key=api_key)

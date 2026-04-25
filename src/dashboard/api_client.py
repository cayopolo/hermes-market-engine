import httpx

from src.config import settings
from src.logging_config import get_logger

logger = get_logger(__name__)


class ApiClient:
    def __init__(self) -> None:
        self._base = settings.api_base_url
        self._client = httpx.Client(base_url=self._base, timeout=2.0)

    def get(self, path: str, **params: object) -> dict | list | None:
        try:
            r = self._client.get(path, params=params)
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            logger.warning("API request failed %s: %s", path, exc)
            return None


api = ApiClient()

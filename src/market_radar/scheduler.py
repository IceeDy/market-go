import os
import time
from datetime import datetime, timezone

from .core import MercadoLivre
from .db import init_db
from .service import collect_category

def configured_categories() -> list[str]:
    raw = os.getenv("ML_RADAR_CATEGORIES", "")
    return [x.strip() for x in raw.split(",") if x.strip()]

def run_once() -> dict:
    init_db()
    client = MercadoLivre(
        os.getenv("ML_ACCESS_TOKEN"),
        os.getenv("ML_API_BASE_URL", "https://api.mercadolibre.com"),
        os.getenv("MLB_SITE_ID", "MLB"),
    )
    categories = configured_categories()
    result = {"started_at": datetime.now(timezone.utc).isoformat(), "categories": categories, "stored": 0}
    for category in categories:
        result["stored"] += collect_category(client, category)
    result["finished_at"] = datetime.now(timezone.utc).isoformat()
    return result

def run_forever(interval_minutes: int = 30):
    while True:
        try:
            print(run_once(), flush=True)
        except Exception as exc:
            print({"error": str(exc)}, flush=True)
        time.sleep(max(1, interval_minutes) * 60)

if __name__ == "__main__":
    run_forever(int(os.getenv("ML_RADAR_INTERVAL_MINUTES", "30")))

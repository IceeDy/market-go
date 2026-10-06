import os
from fastapi import FastAPI, Query

from .core import MercadoLivre
from .db import init_db
from .service import collect_category, persist_best_sellers, persist_search, radar_opportunities, trending_opportunities

app = FastAPI(title="Market Radar", version="0.5.0")

@app.on_event("startup")
def startup():
    init_db()

def ml():
    return MercadoLivre(
        os.getenv("ML_ACCESS_TOKEN"),
        os.getenv("ML_API_BASE_URL", "https://api.mercadolivre.com"),
        os.getenv("MLB_SITE_ID", "MLB"),
    )

@app.get("/health")
def health():
    return {"status": "ok", "version": "0.5.0"}

@app.get("/mercadolivre/search")
def search(q: str = Query(min_length=2), limit: int = Query(20, ge=1, le=50)):
    products = ml().search(q, limit)
    persist_search(products)
    return {"products": [x.__dict__ for x in products], "stored": len(products)}

@app.get("/mercadolivre/highlights/{category}")
def highlights(category: str, limit: int = Query(20, ge=1, le=20)):
    client = ml()
    entries = client.highlights(category, limit)
    ids = [x["id"] for x in entries if x.get("type") == "ITEM"]
    items = client.bulk_items(ids)
    ranking = [
        {"position": x.get("position"), "type": x.get("type"), "id": x.get("id"), "item": items.get(x.get("id"))}
        for x in entries
    ]
    stored = persist_best_sellers(category, ranking)
    return {"ranking": ranking, "stored": stored}

@app.post("/radar/collect/{category}")
def radar_collect(category: str):
    return {"category": category, "stored": collect_category(ml(), category)}

@app.get("/mercadolivre/trends")
def trends(category: str | None = None):
    return {"trends": ml().trends(category)}

@app.get("/mercadolivre/opportunities/trending")
def opportunities(limit: int = Query(50, ge=1, le=200)):
    return {"opportunities": trending_opportunities(limit)}

@app.get("/radar/opportunities")
def radar(
    limit: int = Query(50, ge=1, le=200),
    cost: float | None = Query(None, gt=0),
):
    return {"opportunities": radar_opportunities(limit, cost)}

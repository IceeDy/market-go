import httpx
from dataclasses import dataclass

@dataclass
class MLProduct:
    external_id: str
    title: str
    category_id: str | None = None
    permalink: str | None = None
    price: float | None = None
    position: int = 0

class MercadoLivre:
    def __init__(self, token=None, base="https://api.mercadolibre.com", site="MLB", client=None):
        self.base = base.rstrip("/")
        self.site = site
        self.token = token
        self.client = client or httpx.Client(timeout=20)

    def get(self, path, **kwargs):
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        response = self.client.get(self.base + path, headers=headers, **kwargs)
        response.raise_for_status()
        return response.json()

    def search(self, q, limit=20):
        data = self.get(f"/sites/{self.site}/search", params={"q": q, "limit": min(limit, 50)})
        return [MLProduct(x["id"], x.get("title", ""), x.get("category_id"), x.get("permalink"), x.get("price"), i) for i, x in enumerate(data.get("results", []), 1)]

    def highlights(self, category, limit=20):
        return self.get(f"/highlights/{self.site}/category/{category}").get("content", [])[:limit]

    def bulk_items(self, ids):
        out = {}
        for i in range(0, len(ids), 20):
            rows = self.get("/items/bulk", params={"ids": ",".join(ids[i:i + 20])})
            for row in rows:
                if row.get("status_code") == 200 and row.get("body"):
                    out[row["id"]] = row["body"]
        return out

    def sale_price(self, item_id):
        return self.get(f"/items/{item_id}/sale_price", params={"context": "channel_marketplace"}).get("amount")

    def price_to_win(self, item_id):
        return self.get(
            f"/items/{item_id}/price_to_win",
            params={"siteId": self.site, "version": "v2"},
        )

    def trends(self, category=None):
        path = f"/trends/{self.site}" + (f"/{category}" if category else "")
        data = self.get(path)
        return data if isinstance(data, list) else data.get("trends", data.get("content", []))

def trend_score(current_rank, previous_rank, price_change_pct, observations):
    rank_delta = (previous_rank - current_rank) if current_rank and previous_rank else 0
    rank_signal = max(0, min(100, 50 + rank_delta * 10))
    price_signal = 50 if price_change_pct is None else max(0, min(100, 50 + price_change_pct * 2))
    history_signal = min(100, observations * 10)
    return round(.60 * rank_signal + .25 * price_signal + .15 * history_signal, 2)

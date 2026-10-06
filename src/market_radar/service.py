from datetime import datetime, timezone
from sqlalchemy import desc, select
from .db import SessionLocal
from .models import BestSellerSnapshot, MarketSnapshot, Product
from .core import MLProduct

def upsert_product(session, item: MLProduct) -> Product:
    product = session.scalar(select(Product).where(Product.external_id == item.external_id))
    if not product:
        product = Product(external_id=item.external_id, title=item.title, category_id=item.category_id, permalink=item.permalink)
        session.add(product)
        session.flush()
    else:
        product.title = item.title or product.title
        product.category_id = item.category_id or product.category_id
        product.permalink = item.permalink or product.permalink
    return product

def persist_search(items: list[MLProduct]) -> int:
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        count = 0
        for item in items:
            product = upsert_product(session, item)
            session.add(MarketSnapshot(product_id=product.id, price=item.price, source="search", position=item.position, captured_at=now))
            count += 1
        session.commit()
        return count

def persist_best_sellers(category_id: str, ranking: list[dict]) -> int:
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        count = 0
        for row in ranking:
            item = row.get("item") or {}
            item_id = item.get("id") or row.get("id")
            if not item_id or row.get("type") != "ITEM":
                continue
            product = upsert_product(session, MLProduct(
                external_id=item_id,
                title=item.get("title", ""),
                category_id=item.get("category_id"),
                permalink=item.get("permalink"),
                price=item.get("price"),
                position=int(row.get("position") or 0),
            ))
            session.add(BestSellerSnapshot(product_id=product.id, category_id=category_id, position=int(row.get("position") or 0), element_type=row.get("type","ITEM"), captured_at=now))
            session.add(MarketSnapshot(product_id=product.id, price=item.get("price"), source="best_seller", position=int(row.get("position") or 0), captured_at=now))
            count += 1
        session.commit()
        return count

def trending_opportunities(limit: int = 50) -> list[dict]:
    with SessionLocal() as session:
        rows = session.execute(select(Product, MarketSnapshot).join(MarketSnapshot, MarketSnapshot.product_id == Product.id).order_by(Product.id, desc(MarketSnapshot.captured_at))).all()
        history: dict[int, list[tuple[Product, MarketSnapshot]]] = {}
        for product, snap in rows:
            history.setdefault(product.id, []).append((product, snap))
        result = []
        for entries in history.values():
            product, latest = entries[0]
            previous = entries[1] if len(entries) > 1 else None
            price_change = None
            if previous and previous[1].price and latest.price is not None:
                price_change = round((latest.price - previous[1].price) / previous[1].price * 100, 2)
            rank_delta = 0
            if previous and previous[1].position and latest.position:
                rank_delta = previous[1].position - latest.position
            score = round(max(0, min(100, 50 + rank_delta * 12 + (price_change or 0) * 1.5 + min(len(entries), 5) * 4)), 2)
            result.append({
                "external_id": product.external_id,
                "title": product.title,
                "price": latest.price,
                "price_change_pct": price_change,
                "rank_delta": rank_delta,
                "observations": len(entries),
                "score": score,
                "permalink": product.permalink,
            })
        return sorted(result, key=lambda x: x["score"], reverse=True)[:limit]

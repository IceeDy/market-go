import json
from datetime import datetime, timezone

from sqlalchemy import desc, select

from .core import MLProduct, MercadoLivre
from .db import SessionLocal
from .models import BestSellerSnapshot, CompetitionSnapshot, MarketSnapshot, Product
from .scoring import radar_score

def upsert_product(session, item: MLProduct) -> Product:
    product = session.scalar(select(Product).where(Product.external_id == item.external_id))
    if not product:
        product = Product(
            external_id=item.external_id,
            title=item.title,
            category_id=item.category_id,
            permalink=item.permalink,
        )
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
        for item in items:
            product = upsert_product(session, item)
            session.add(MarketSnapshot(
                product_id=product.id, price=item.price, source="search",
                position=item.position, captured_at=now,
            ))
        session.commit()
        return len(items)

def persist_best_sellers(category_id: str, ranking: list[dict]) -> int:
    now = datetime.now(timezone.utc)
    count = 0
    with SessionLocal() as session:
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
            position = int(row.get("position") or 0)
            session.add(BestSellerSnapshot(
                product_id=product.id,
                category_id=category_id,
                position=position,
                element_type=row.get("type", "ITEM"),
                captured_at=now,
            ))
            session.add(MarketSnapshot(
                product_id=product.id,
                price=item.get("price"),
                source="best_seller",
                position=position,
                captured_at=now,
            ))
            count += 1
        session.commit()
    return count

def collect_category(client: MercadoLivre, category_id: str) -> int:
    entries = client.highlights(category_id, 20)
    ids = [x["id"] for x in entries if x.get("type") == "ITEM"]
    items = client.bulk_items(ids)
    now = datetime.now(timezone.utc)
    stored = 0
    with SessionLocal() as session:
        for row in entries:
            if row.get("type") != "ITEM":
                continue
            item_id = row.get("id")
            item = items.get(item_id)
            if not item:
                continue
            product = upsert_product(session, MLProduct(
                external_id=item_id,
                title=item.get("title", ""),
                category_id=item.get("category_id"),
                permalink=item.get("permalink"),
                price=item.get("price"),
                position=int(row.get("position") or 0),
            ))
            position = int(row.get("position") or 0)
            sale_price = None
            competition = None
            try:
                sale_price = client.sale_price(item_id)
            except Exception:
                sale_price = item.get("price")
            try:
                competition = client.price_to_win(item_id)
            except Exception:
                competition = None

            session.add(BestSellerSnapshot(
                product_id=product.id,
                category_id=category_id,
                position=position,
                element_type="ITEM",
                captured_at=now,
            ))
            session.add(MarketSnapshot(
                product_id=product.id,
                price=sale_price,
                source="best_seller",
                position=position,
                captured_at=now,
            ))
            if competition:
                session.add(CompetitionSnapshot(
                    product_id=product.id,
                    item_id=item_id,
                    status=competition.get("status"),
                    current_price=competition.get("current_price"),
                    price_to_win=competition.get("price_to_win"),
                    boosts=json.dumps(competition.get("boosts", []), ensure_ascii=False),
                    captured_at=now,
                ))
            stored += 1
        session.commit()
    return stored

def trending_opportunities(limit: int = 50) -> list[dict]:
    with SessionLocal() as session:
        rows = session.execute(
            select(Product, MarketSnapshot)
            .join(MarketSnapshot, MarketSnapshot.product_id == Product.id)
            .order_by(Product.id, desc(MarketSnapshot.captured_at))
        ).all()
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
            result.append({
                "external_id": product.external_id,
                "title": product.title,
                "price": latest.price,
                "price_change_pct": price_change,
                "observations": len(entries),
                "permalink": product.permalink,
            })
        return result[:limit]

def radar_opportunities(limit: int = 50, cost: float | None = None) -> list[dict]:
    with SessionLocal() as session:
        products = session.scalars(select(Product)).all()
        result = []
        for product in products:
            snaps = session.scalars(
                select(BestSellerSnapshot)
                .where(BestSellerSnapshot.product_id == product.id)
                .order_by(desc(BestSellerSnapshot.captured_at))
            ).all()
            if not snaps:
                continue
            latest = snaps[0]
            previous = snaps[1] if len(snaps) > 1 else None
            rank_delta = previous.position - latest.position if previous else 0
            market = session.scalar(
                select(MarketSnapshot)
                .where(MarketSnapshot.product_id == product.id)
                .order_by(desc(MarketSnapshot.captured_at))
            )
            competition = session.scalar(
                select(CompetitionSnapshot)
                .where(CompetitionSnapshot.product_id == product.id)
                .order_by(desc(CompetitionSnapshot.captured_at))
            )
            price = (competition.current_price if competition and competition.current_price else None)
            price = price or (market.price if market else None)
            margin = ((price - cost) / price * 100) if price and cost and price > 0 else None
            score = radar_score(
                position=latest.position,
                rank_delta=rank_delta,
                observations=len(snaps),
                price=price,
                cost=cost,
                competition_status=competition.status if competition else None,
                margin=margin,
            )
            result.append({
                "score": score,
                "external_id": product.external_id,
                "title": product.title,
                "category_id": product.category_id,
                "position": latest.position,
                "rank_delta": rank_delta,
                "observations": len(snaps),
                "price": price,
                "cost": cost,
                "margin_pct": round(margin, 2) if margin is not None else None,
                "competition_status": competition.status if competition else None,
                "price_to_win": competition.price_to_win if competition else None,
                "permalink": product.permalink,
            })
        return sorted(result, key=lambda x: x["score"], reverse=True)[:limit]

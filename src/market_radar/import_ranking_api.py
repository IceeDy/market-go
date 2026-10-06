import os

from fastapi import APIRouter
from pydantic import BaseModel, Field

from .core import MercadoLivre
from .import_ranking import ImportBudget, rank_import_candidates
from .listing_prices import resolve_listing_cost
from .service import radar_opportunities


router = APIRouter(prefix="/radar/import-ranking", tags=["radar"])


class ImportCandidate(BaseModel):
    external_id: str | None = None
    title: str | None = None
    category_id: str | None = None
    permalink: str | None = None
    radar_score: float = Field(default=0, ge=0)
    selling_price: float | None = Field(default=None, gt=0)
    price: float | None = Field(default=None, gt=0)
    unit_cost: float = Field(gt=0)
    international_freight_per_unit: float = Field(default=0, ge=0)
    import_tax_pct: float = Field(default=0, ge=0)
    domestic_cost_per_unit: float = Field(default=0, ge=0)
    other_cost_per_unit: float = Field(default=0, ge=0)
    marketplace_fee_pct: float = Field(default=0, ge=0)
    fixed_marketplace_fee: float = Field(default=0, ge=0)
    shipping_cost_per_unit: float = Field(default=0, ge=0)
    currency_id: str = Field(default="BRL")
    listing_type_id: str = Field(default="gold_special")
    logistic_type: str | None = None
    shipping_mode: str | None = None


class ImportRankingRequest(BaseModel):
    budget: float = Field(gt=0)
    reserve_pct: float = Field(default=10, ge=0, lt=100)
    min_units: int = Field(default=1, ge=1)
    use_ml_fees: bool = True
    candidates: list[ImportCandidate] = Field(min_length=1)


class RadarImportRequest(BaseModel):
    budget: float = Field(gt=0)
    reserve_pct: float = Field(default=10, ge=0, lt=100)
    min_units: int = Field(default=1, ge=1)
    radar_limit: int = Field(default=50, ge=1, le=200)
    sourcing_cost_pct: float = Field(default=30, gt=0, lt=100)
    international_freight_pct: float = Field(default=10, ge=0, lt=100)
    import_tax_pct: float = Field(default=0, ge=0, lt=100)
    domestic_cost_per_unit: float = Field(default=0, ge=0)
    other_cost_per_unit: float = Field(default=0, ge=0)
    shipping_cost_per_unit: float = Field(default=0, ge=0)
    listing_type_id: str = Field(default="gold_special")
    logistic_type: str | None = None
    shipping_mode: str | None = None
    use_ml_fees: bool = True


def _ml_client() -> MercadoLivre:
    return MercadoLivre(
        os.getenv("ML_ACCESS_TOKEN"),
        os.getenv("ML_API_BASE_URL", "https://api.mercadolivre.com"),
        os.getenv("MLB_SITE_ID", "MLB"),
    )


def _apply_ml_fee(client: MercadoLivre, row: dict, request) -> None:
    price = row.get("selling_price") or row.get("price")
    if not request.use_ml_fees or not row.get("category_id") or not price:
        return
    try:
        fee = resolve_listing_cost(
            client=client,
            category_id=row["category_id"],
            price=price,
            currency_id="BRL",
            listing_type_id=request.listing_type_id,
            logistic_type=request.logistic_type,
            shipping_mode=request.shipping_mode,
        )
        if fee and fee.get("sale_fee_amount") is not None:
            row["marketplace_fee_amount"] = float(fee["sale_fee_amount"])
            row["marketplace_fee_source"] = "mercado_livre"
            row["marketplace_fee_pct_effective"] = float(
                fee.get("sale_fee_details", {}).get("percentage_fee", 0)
            )
    except Exception:
        row["marketplace_fee_source"] = "manual_fallback"


def _rank(request, payload: list[dict]):
    return rank_import_candidates(
        payload,
        ImportBudget(
            budget=request.budget,
            reserve_pct=request.reserve_pct,
            min_units=request.min_units,
        ),
    )


@router.post("")
def import_ranking(request: ImportRankingRequest):
    client = _ml_client()
    payload = []

    for candidate in request.candidates:
        row = candidate.model_dump()
        _apply_ml_fee(client, row, request)
        payload.append(row)

    result = _rank(request, payload)
    return {
        "budget": request.budget,
        "reserve_pct": request.reserve_pct,
        "investable_budget": round(request.budget * (1 - request.reserve_pct / 100), 2),
        "use_ml_fees": request.use_ml_fees,
        "candidates": result,
    }


@router.post("/from-radar")
def import_ranking_from_radar(request: RadarImportRequest):
    client = _ml_client()
    opportunities = radar_opportunities(limit=request.radar_limit)
    payload = []

    for opportunity in opportunities:
        price = opportunity.get("price")
        if not price or price <= 0 or not opportunity.get("category_id"):
            continue

        # MVP estimate: sourcing cost is a percentage of the observed ML sale price.
        # Replace with supplier quotations when the sourcing module is connected.
        unit_cost = price * request.sourcing_cost_pct / 100

        row = {
            "external_id": opportunity.get("external_id"),
            "title": opportunity.get("title"),
            "category_id": opportunity.get("category_id"),
            "permalink": opportunity.get("permalink"),
            "radar_score": opportunity.get("score", 0),
            "selling_price": price,
            "unit_cost": unit_cost,
            "international_freight_per_unit": price * request.international_freight_pct / 100,
            "import_tax_pct": request.import_tax_pct,
            "domestic_cost_per_unit": request.domestic_cost_per_unit,
            "other_cost_per_unit": request.other_cost_per_unit,
            "shipping_cost_per_unit": request.shipping_cost_per_unit,
        }
        _apply_ml_fee(client, row, request)
        payload.append(row)

    result = _rank(request, payload)
    return {
        "mode": "radar_to_import",
        "budget": request.budget,
        "reserve_pct": request.reserve_pct,
        "investable_budget": round(request.budget * (1 - request.reserve_pct / 100), 2),
        "radar_candidates": len(opportunities),
        "eligible_candidates": len(payload),
        "sourcing_cost_pct": request.sourcing_cost_pct,
        "international_freight_pct": request.international_freight_pct,
        "use_ml_fees": request.use_ml_fees,
        "candidates": result,
    }

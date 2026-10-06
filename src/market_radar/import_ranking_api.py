import os

from fastapi import APIRouter
from pydantic import BaseModel, Field

from .core import MercadoLivre
from .import_ranking import ImportBudget, rank_import_candidates
from .listing_prices import resolve_listing_cost


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


def _ml_client() -> MercadoLivre:
    return MercadoLivre(
        os.getenv("ML_ACCESS_TOKEN"),
        os.getenv("ML_API_BASE_URL", "https://api.mercadolivre.com"),
        os.getenv("MLB_SITE_ID", "MLB"),
    )


@router.post("")
def import_ranking(request: ImportRankingRequest):
    client = _ml_client()
    payload = []

    for candidate in request.candidates:
        row = candidate.model_dump()
        price = row.get("selling_price") or row.get("price")

        if request.use_ml_fees and row.get("category_id") and price:
            try:
                fee = resolve_listing_cost(
                    client=client,
                    category_id=row["category_id"],
                    price=price,
                    currency_id=row["currency_id"],
                    listing_type_id=row["listing_type_id"],
                    logistic_type=row.get("logistic_type"),
                    shipping_mode=row.get("shipping_mode"),
                )
                if fee and fee.get("sale_fee_amount") is not None:
                    row["marketplace_fee_amount"] = float(fee["sale_fee_amount"])
                    row["marketplace_fee_source"] = "mercado_livre"
                    row["marketplace_fee_pct_effective"] = (
                        float(fee.get("sale_fee_details", {}).get("percentage_fee", 0))
                    )
            except Exception:
                row["marketplace_fee_source"] = "manual_fallback"

        payload.append(row)

    result = rank_import_candidates(
        payload,
        ImportBudget(
            budget=request.budget,
            reserve_pct=request.reserve_pct,
            min_units=request.min_units,
        ),
    )
    return {
        "budget": request.budget,
        "reserve_pct": request.reserve_pct,
        "investable_budget": round(request.budget * (1 - request.reserve_pct / 100), 2),
        "use_ml_fees": request.use_ml_fees,
        "candidates": result,
    }

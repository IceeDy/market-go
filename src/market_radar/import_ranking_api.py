from fastapi import APIRouter
from pydantic import BaseModel, Field

from .import_ranking import ImportBudget, rank_import_candidates


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


class ImportRankingRequest(BaseModel):
    budget: float = Field(gt=0)
    reserve_pct: float = Field(default=10, ge=0, lt=100)
    min_units: int = Field(default=1, ge=1)
    candidates: list[ImportCandidate] = Field(min_length=1)


@router.post("")
def import_ranking(request: ImportRankingRequest):
    payload = [candidate.model_dump() for candidate in request.candidates]
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
        "candidates": result,
    }

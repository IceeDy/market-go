from fastapi import APIRouter
from pydantic import BaseModel, Field
from .economics import SourcingScenario, economics

router = APIRouter(prefix="/radar/economics", tags=["radar"])

class EconomicsRequest(BaseModel):
    selling_price: float = Field(gt=0)
    unit_cost: float = Field(ge=0)
    international_freight_per_unit: float = Field(default=0, ge=0)
    import_tax_pct: float = Field(default=0, ge=0)
    domestic_cost_per_unit: float = Field(default=0, ge=0)
    other_cost_per_unit: float = Field(default=0, ge=0)
    marketplace_fee_pct: float = Field(default=0, ge=0)
    fixed_marketplace_fee: float = Field(default=0, ge=0)
    shipping_cost_per_unit: float = Field(default=0, ge=0)

@router.post("")
def calculate(request: EconomicsRequest):
    scenario = SourcingScenario(
        unit_cost=request.unit_cost,
        international_freight_per_unit=request.international_freight_per_unit,
        import_tax_pct=request.import_tax_pct,
        domestic_cost_per_unit=request.domestic_cost_per_unit,
        other_cost_per_unit=request.other_cost_per_unit,
        marketplace_fee_pct=request.marketplace_fee_pct,
        fixed_marketplace_fee=request.fixed_marketplace_fee,
        shipping_cost_per_unit=request.shipping_cost_per_unit,
    )
    return economics(request.selling_price, scenario)

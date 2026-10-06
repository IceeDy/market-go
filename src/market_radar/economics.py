from dataclasses import dataclass

@dataclass(frozen=True)
class SourcingScenario:
    unit_cost: float
    international_freight_per_unit: float = 0.0
    import_tax_pct: float = 0.0
    domestic_cost_per_unit: float = 0.0
    other_cost_per_unit: float = 0.0
    marketplace_fee_pct: float = 0.0
    fixed_marketplace_fee: float = 0.0
    shipping_cost_per_unit: float = 0.0

    @property
    def landed_cost(self) -> float:
        taxable = self.unit_cost + self.international_freight_per_unit
        tax = taxable * self.import_tax_pct / 100
        return taxable + tax + self.domestic_cost_per_unit + self.other_cost_per_unit

def economics(price: float, scenario: SourcingScenario) -> dict:
    if price <= 0:
        raise ValueError("price must be positive")
    landed = scenario.landed_cost
    marketplace_fee = price * scenario.marketplace_fee_pct / 100 + scenario.fixed_marketplace_fee
    total_cost = landed + marketplace_fee + scenario.shipping_cost_per_unit
    profit = price - total_cost
    margin = profit / price * 100
    roi = profit / landed * 100 if landed > 0 else 0.0
    return {
        "selling_price": round(price, 2),
        "landed_cost": round(landed, 2),
        "marketplace_fee": round(marketplace_fee, 2),
        "shipping_cost": round(scenario.shipping_cost_per_unit, 2),
        "total_cost": round(total_cost, 2),
        "profit": round(profit, 2),
        "margin_pct": round(margin, 2),
        "roi_pct": round(roi, 2),
    }

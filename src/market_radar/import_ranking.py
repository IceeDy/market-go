from dataclasses import dataclass
from math import floor

from .economics import SourcingScenario, economics


@dataclass(frozen=True)
class ImportBudget:
    budget: float
    reserve_pct: float = 10.0
    min_units: int = 1

    @property
    def investable_budget(self) -> float:
        return self.budget * (1 - self.reserve_pct / 100)


def rank_import_candidates(candidates: list[dict], budget: ImportBudget, default_scenario: dict | None = None) -> list[dict]:
    if budget.budget <= 0:
        raise ValueError("budget must be positive")
    if not 0 <= budget.reserve_pct < 100:
        raise ValueError("reserve_pct must be between 0 and 100")

    default_scenario = default_scenario or {}
    ranked = []

    for candidate in candidates:
        price = float(candidate.get("selling_price") or candidate.get("price") or 0)
        unit_cost = float(candidate.get("unit_cost") or 0)
        if price <= 0 or unit_cost <= 0:
            continue

        scenario = SourcingScenario(
            unit_cost=unit_cost,
            international_freight_per_unit=float(candidate.get("international_freight_per_unit", default_scenario.get("international_freight_per_unit", 0))),
            import_tax_pct=float(candidate.get("import_tax_pct", default_scenario.get("import_tax_pct", 0))),
            domestic_cost_per_unit=float(candidate.get("domestic_cost_per_unit", default_scenario.get("domestic_cost_per_unit", 0))),
            other_cost_per_unit=float(candidate.get("other_cost_per_unit", default_scenario.get("other_cost_per_unit", 0))),
            marketplace_fee_pct=float(candidate.get("marketplace_fee_pct", default_scenario.get("marketplace_fee_pct", 0))),
            fixed_marketplace_fee=float(candidate.get("fixed_marketplace_fee", default_scenario.get("fixed_marketplace_fee", 0))),
            shipping_cost_per_unit=float(candidate.get("shipping_cost_per_unit", default_scenario.get("shipping_cost_per_unit", 0))),
        )
        unit = economics(price, scenario)
        units = floor(budget.investable_budget / unit["landed_cost"]) if unit["landed_cost"] > 0 else 0
        if units < budget.min_units:
            continue

        invested = units * unit["landed_cost"]
        revenue = units * price
        profit = units * unit["profit"]
        capital_remaining = budget.budget - invested
        radar_score = float(candidate.get("score") or 0)
        roi = profit / invested * 100 if invested > 0 else 0

        ranked.append({
            "external_id": candidate.get("external_id"),
            "title": candidate.get("title"),
            "category_id": candidate.get("category_id"),
            "permalink": candidate.get("permalink"),
            "radar_score": round(radar_score, 2),
            "selling_price": price,
            "unit_landed_cost": unit["landed_cost"],
            "units": units,
            "capital_invested": round(invested, 2),
            "capital_remaining": round(capital_remaining, 2),
            "revenue_potential": round(revenue, 2),
            "profit_per_unit": unit["profit"],
            "profit_potential": round(profit, 2),
            "margin_pct": unit["margin_pct"],
            "roi_pct": round(roi, 2),
        })

    return sorted(
        ranked,
        key=lambda x: (x["profit_potential"], x["roi_pct"], x["radar_score"]),
        reverse=True,
    )

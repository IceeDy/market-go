def clamp(value, low=0.0, high=100.0):
    return max(low, min(high, value))

def opportunity_score(demand, growth, competition, price, margin, logistics, risk):
    return round(
        0.22 * demand + 0.18 * growth + 0.15 * competition +
        0.10 * price + 0.20 * margin + 0.10 * logistics + 0.05 * risk, 2
    )

def competition_signal(status):
    return {
        "winning": 95,
        "sharing_first_place": 80,
        "competing": 60,
        "losing": 35,
        "listed": 15,
    }.get(status, 50)

def radar_score(position, rank_delta, observations, price, cost,
                competition_status=None, margin=None):
    demand = clamp(100 - (max(position, 1) - 1) * 5)
    growth = clamp(50 + rank_delta * 12)
    competition = competition_signal(competition_status)
    price_signal = 50
    if price and price > 0:
        price_signal = clamp(35 + min(price / 2, 65))
    margin_signal = clamp(margin) if margin is not None else 50
    history = clamp(observations * 15)
    growth = clamp((growth * 0.75) + (history * 0.25))
    return opportunity_score(
        demand, growth, competition, price_signal, margin_signal, 70, 70
    )

def commercial_score(price, cost, competition, observations, rank_delta=0):
    if price is None or price <= 0 or cost is None or cost <= 0:
        margin = 0
    else:
        margin = clamp((price - cost) / price * 100)
    demand = clamp(observations * 15)
    growth = clamp(50 + rank_delta * 10)
    comp = clamp(competition)
    price_signal = clamp(price / 10) if price else 0
    return opportunity_score(demand, growth, comp, price_signal, margin, 70, 70)

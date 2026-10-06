def clamp(value, low=0.0, high=100.0):
    return max(low, min(high, value))

def opportunity_score(demand, growth, competition, price, margin, logistics, risk):
    return round(0.22*demand + 0.18*growth + 0.15*competition + 0.10*price + 0.20*margin + 0.10*logistics + 0.05*risk, 2)

def commercial_score(price, cost, competition, observations, rank_delta=0):
    if price is None or price <= 0 or cost is None or cost <= 0:
        margin = 0
    else:
        margin = clamp((price - cost) / price * 100)
    demand = clamp(observations * 15)
    growth = clamp(50 + rank_delta * 10)
    comp = clamp(100 - competition * 10)
    price_signal = clamp(price / 10) if price else 0
    return opportunity_score(demand, growth, comp, price_signal, margin, 70, 70)

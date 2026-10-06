from .core import MercadoLivre

def competition_snapshot(client: MercadoLivre, item_id: str) -> dict:
    return client.price_to_win(item_id)

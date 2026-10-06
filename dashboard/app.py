import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

import pandas as pd
import streamlit as st
from market_radar.core import MercadoLivre
from market_radar.db import init_db
from market_radar.service import persist_best_sellers, persist_search, trending_opportunities

st.set_page_config(page_title="Market Radar", layout="wide")
st.title("Market Radar")
st.caption("v0.4 — product hunting + Opportunity Radar")
init_db()
c = MercadoLivre(os.getenv("ML_ACCESS_TOKEN"), os.getenv("ML_API_BASE_URL", "https://api.mercadolibre.com"), os.getenv("MLB_SITE_ID", "MLB"))

mode = st.sidebar.radio("Modo", ["Busca", "Mais vendidos", "Em alta", "Tendências"])

if mode == "Busca":
    q = st.sidebar.text_input("Produto", "organizador de cozinha")
    n = st.sidebar.slider("Itens", 5, 50, 20)
    if st.button("Pesquisar", type="primary"):
        products = c.search(q, n)
        persist_search(products)
        st.metric("Produtos coletados", len(products))
        st.dataframe(pd.DataFrame([x.__dict__ for x in products]), use_container_width=True, hide_index=True)

elif mode == "Mais vendidos":
    cat = st.sidebar.text_input("Categoria", "MLB1430")
    if st.button("Buscar", type="primary"):
        entries = c.highlights(cat)
        ids = [x["id"] for x in entries if x.get("type") == "ITEM"]
        items = c.bulk_items(ids)
        rows = [{"posição": x.get("position"), "tipo": x.get("type"), "id": x.get("id"), "título": (items.get(x.get("id")) or {}).get("title"), "preço": (items.get(x.get("id")) or {}).get("price")} for x in entries]
        persist_best_sellers(cat, [{"position": x.get("position"), "type": x.get("type"), "id": x.get("id"), "item": items.get(x.get("id"))} for x in entries])
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

elif mode == "Em alta":
    data = trending_opportunities(100)
    st.subheader("Opportunity Radar")
    st.caption("Score inicial: ranking + variação de preço + quantidade de observações.")
    if not data:
        st.info("Ainda não há histórico. Faça algumas buscas ou colete um ranking para alimentar o radar.")
    else:
        df = pd.DataFrame(data)
        st.dataframe(df[["score", "title", "price", "price_change_pct", "rank_delta", "observations", "external_id", "permalink"]], use_container_width=True, hide_index=True)

else:
    cat = st.sidebar.text_input("Categoria", "")
    if st.button("Buscar tendências", type="primary"):
        st.dataframe(pd.DataFrame(c.trends(cat or None)), use_container_width=True, hide_index=True)

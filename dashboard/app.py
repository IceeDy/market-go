import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

import pandas as pd
import streamlit as st

from market_radar.core import MercadoLivre
from market_radar.db import init_db
from market_radar.import_ranking_api import RadarImportRequest, import_ranking_from_radar
from market_radar.service import persist_best_sellers, persist_search, trending_opportunities


def _load_streamlit_config():
    """Load Mercado Livre credentials from Streamlit Secrets or environment."""
    token = os.getenv("ML_ACCESS_TOKEN", "")
    if not token:
        try:
            token = str(st.secrets.get("ML_ACCESS_TOKEN", ""))
        except Exception:
            token = ""
    if token:
        os.environ["ML_ACCESS_TOKEN"] = token
    return token


ML_ACCESS_TOKEN = _load_streamlit_config()

st.set_page_config(page_title="Market Radar", layout="wide")
st.title("Market Radar")
st.caption("v0.5 — product hunting + Opportunity Radar + Import Ranking")
init_db()

if not ML_ACCESS_TOKEN:
    st.sidebar.warning("Mercado Livre não configurado. Adicione ML_ACCESS_TOKEN em Settings → Secrets no Streamlit Cloud.")

c = MercadoLivre(
    os.getenv("ML_ACCESS_TOKEN"),
    os.getenv("ML_API_BASE_URL", "https://api.mercadolibre.com"),
    os.getenv("MLB_SITE_ID", "MLB"),
)

mode = st.sidebar.radio(
    "Modo",
    ["Busca", "Mais vendidos", "Em alta", "Tendências", "Importação"],
)

if mode == "Busca":
    q = st.sidebar.text_input("Produto", "organizador de cozinha")
    n = st.sidebar.slider("Itens", 5, 50, 20)
    if st.button("Pesquisar", type="primary"):
        if not ML_ACCESS_TOKEN:
            st.error("Configure o secret ML_ACCESS_TOKEN no Streamlit Cloud antes de pesquisar.")
            st.stop()
        try:
            products = c.search(q, n)
        except Exception as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status == 401:
                st.error("Mercado Livre rejeitou a autenticação (401). O ML_ACCESS_TOKEN está ausente, expirado ou inválido.")
                st.stop()
            st.error(f"Erro ao consultar o Mercado Livre: {exc}")
            st.stop()
        persist_search(products)
        st.metric("Produtos coletados", len(products))
        st.dataframe(
            pd.DataFrame([x.__dict__ for x in products]),
            use_container_width=True,
            hide_index=True,
        )

elif mode == "Mais vendidos":
    cat = st.sidebar.text_input("Categoria", "MLB1430")
    if st.button("Buscar", type="primary"):
        entries = c.highlights(cat)
        ids = [x["id"] for x in entries if x.get("type") == "ITEM"]
        items = c.bulk_items(ids)
        rows = [
            {
                "posição": x.get("position"),
                "tipo": x.get("type"),
                "id": x.get("id"),
                "título": (items.get(x.get("id")) or {}).get("title"),
                "preço": (items.get(x.get("id")) or {}).get("price"),
            }
            for x in entries
        ]
        persist_best_sellers(
            cat,
            [
                {
                    "position": x.get("position"),
                    "type": x.get("type"),
                    "id": x.get("id"),
                    "item": items.get(x.get("id")),
                }
                for x in entries
            ],
        )
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

elif mode == "Em alta":
    data = trending_opportunities(100)
    st.subheader("Opportunity Radar")
    st.caption("Histórico de preço e coleta para identificar produtos que merecem investigação.")
    if not data:
        st.info("Ainda não há histórico. Faça algumas buscas ou colete um ranking para alimentar o radar.")
    else:
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)

elif mode == "Tendências":
    cat = st.sidebar.text_input("Categoria", "")
    if st.button("Buscar tendências", type="primary"):
        st.dataframe(pd.DataFrame(c.trends(cat or None)), use_container_width=True, hide_index=True)

else:
    st.subheader("Importação — Top produtos")
    st.caption(
        "Transforma as oportunidades já coletadas pelo Radar em um ranking de compra. "
        "O custo de origem ainda é uma estimativa percentual do preço de venda."
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        budget = st.number_input("Capital disponível (R$)", min_value=100.0, value=20000.0, step=1000.0)
        reserve_pct = st.number_input("Reserva (%)", min_value=0.0, max_value=90.0, value=15.0, step=1.0)
        radar_limit = st.slider("Oportunidades analisadas", 10, 200, 50)
    with col2:
        sourcing_cost_pct = st.number_input(
            "Custo de compra (% do preço)",
            min_value=1.0,
            max_value=90.0,
            value=30.0,
            step=1.0,
            help="Estimativa temporária. Depois será substituída por cotação real de fornecedor.",
        )
        freight_pct = st.number_input(
            "Frete internacional (% do preço)",
            min_value=0.0,
            max_value=50.0,
            value=10.0,
            step=1.0,
        )
        import_tax_pct = st.number_input("Imposto de importação (%)", min_value=0.0, max_value=100.0, value=0.0, step=1.0)
    with col3:
        domestic_cost = st.number_input("Custo doméstico/unid. (R$)", min_value=0.0, value=0.0, step=1.0)
        other_cost = st.number_input("Outros custos/unid. (R$)", min_value=0.0, value=0.0, step=1.0)
        shipping_cost = st.number_input("Frete ao cliente/unid. (R$)", min_value=0.0, value=0.0, step=1.0)

    use_ml_fees = st.checkbox(
        "Usar custos reais do Mercado Livre",
        value=True,
        help="Consulta Listing Prices para estimar a tarifa de venda por categoria/preço.",
    )
    listing_type = st.selectbox(
        "Tipo de anúncio",
        ["gold_special", "gold_pro", "free"],
        index=0,
        help="O custo pode variar conforme anúncio e logística.",
    )

    if st.button("Analisar melhores produtos para importar", type="primary", use_container_width=True):
        request = RadarImportRequest(
            budget=budget,
            reserve_pct=reserve_pct,
            radar_limit=radar_limit,
            sourcing_cost_pct=sourcing_cost_pct,
            international_freight_pct=freight_pct,
            import_tax_pct=import_tax_pct,
            domestic_cost_per_unit=domestic_cost,
            other_cost_per_unit=other_cost,
            shipping_cost_per_unit=shipping_cost,
            listing_type_id=listing_type,
            use_ml_fees=use_ml_fees,
        )

        with st.spinner("Analisando Radar + custos de venda..."):
            try:
                result = import_ranking_from_radar(request)
            except Exception as exc:
                st.error(f"Não foi possível concluir a análise: {exc}")
                st.stop()

        candidates = result.get("candidates", [])
        if not candidates:
            st.warning(
                "Nenhum produto elegível. Primeiro colete dados em 'Mais vendidos' "
                "ou execute a coleta automática do Radar."
            )
        else:
            st.success(
                f"{result['eligible_candidates']} produtos elegíveis de "
                f"{result['radar_candidates']} oportunidades."
            )

            top = candidates[0]
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Melhor produto", (top.get("title") or "")[:32])
            m2.metric("Lucro potencial", f"R$ {top['profit_potential']:,.2f}")
            m3.metric("Margem", f"{top['margin_pct']:.1f}%")
            m4.metric("ROI", f"{top['roi_pct']:.1f}%")

            display = pd.DataFrame(
                [
                    {
                        "rank": i,
                        "produto": row.get("title"),
                        "Radar": row.get("radar_score"),
                        "venda": row.get("selling_price"),
                        "custo landed/unid.": row.get("unit_landed_cost"),
                        "tarifa ML": row.get("marketplace_fee"),
                        "unidades": row.get("units"),
                        "capital": row.get("capital_invested"),
                        "receita potencial": row.get("revenue_potential"),
                        "lucro potencial": row.get("profit_potential"),
                        "margem %": row.get("margin_pct"),
                        "ROI %": row.get("roi_pct"),
                    }
                    for i, row in enumerate(candidates, 1)
                ]
            )
            st.dataframe(
                display,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "venda": st.column_config.NumberColumn(format="R$ %.2f"),
                    "custo landed/unid.": st.column_config.NumberColumn(format="R$ %.2f"),
                    "tarifa ML": st.column_config.NumberColumn(format="R$ %.2f"),
                    "capital": st.column_config.NumberColumn(format="R$ %.2f"),
                    "receita potencial": st.column_config.NumberColumn(format="R$ %.2f"),
                    "lucro potencial": st.column_config.NumberColumn(format="R$ %.2f"),
                    "margem %": st.column_config.NumberColumn(format="%.2f"),
                    "ROI %": st.column_config.NumberColumn(format="%.2f"),
                },
            )

            st.info(
                "Importante: o custo de compra e o frete internacional são estimativas. "
                "Não trate o ranking como decisão de compra até conectarmos fornecedores e custo real desembarcado."
            )

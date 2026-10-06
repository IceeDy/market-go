import os,sys
sys.path.insert(0,os.path.join(os.path.dirname(__file__),"../src"))
import streamlit as st, pandas as pd
from market_radar.core import MercadoLivre
st.set_page_config(page_title="Market Radar",layout="wide")
st.title("Market Radar")
st.caption("v0.3 — product hunting")
c=MercadoLivre(os.getenv("ML_ACCESS_TOKEN"),os.getenv("ML_API_BASE_URL","https://api.mercadolibre.com"),os.getenv("MLB_SITE_ID","MLB"))
mode=st.sidebar.radio("Modo",["Busca","Mais vendidos","Tendências"])
if mode=="Busca":
    q=st.sidebar.text_input("Produto","organizador de cozinha"); n=st.sidebar.slider("Itens",5,50,20)
    if st.button("Pesquisar",type="primary"): st.dataframe(pd.DataFrame([x.__dict__ for x in c.search(q,n)]),use_container_width=True,hide_index=True)
elif mode=="Mais vendidos":
    cat=st.sidebar.text_input("Categoria","MLB1430")
    if st.button("Buscar",type="primary"):
        e=c.highlights(cat); ids=[x["id"] for x in e if x.get("type")=="ITEM"]; items=c.bulk_items(ids)
        st.dataframe(pd.DataFrame([{"posição":x.get("position"),"tipo":x.get("type"),"id":x.get("id"),"título":(items.get(x.get("id")) or {}).get("title")} for x in e]),use_container_width=True,hide_index=True)
else:
    cat=st.sidebar.text_input("Categoria","")
    if st.button("Buscar tendências",type="primary"): st.dataframe(pd.DataFrame(c.trends(cat or None)),use_container_width=True,hide_index=True)

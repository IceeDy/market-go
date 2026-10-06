import os
from fastapi import FastAPI, Query
from .core import MercadoLivre
app=FastAPI(title="Market Radar",version="0.3.0")

def ml(): return MercadoLivre(os.getenv("ML_ACCESS_TOKEN"),os.getenv("ML_API_BASE_URL","https://api.mercadolibre.com"),os.getenv("MLB_SITE_ID","MLB"))
@app.get("/health")
def health(): return {"status":"ok","version":"0.3.0"}
@app.get("/mercadolivre/search")
def search(q:str=Query(min_length=2),limit:int=Query(20,ge=1,le=50)):
    return {"products":[x.__dict__ for x in ml().search(q,limit)]}
@app.get("/mercadolivre/highlights/{category}")
def highlights(category:str,limit:int=Query(20,ge=1,le=20)):
    c=ml(); entries=c.highlights(category,limit); ids=[x["id"] for x in entries if x.get("type")=="ITEM"]; items=c.bulk_items(ids)
    return {"ranking":[{"position":e.get("position"),"type":e.get("type"),"id":e.get("id"),"item":items.get(e.get("id"))} for e in entries]}
@app.get("/mercadolivre/trends")
def trends(category:str|None=None): return {"trends":ml().trends(category)}

# Market Radar

MVP de inteligência de mercado para encontrar oportunidades de produtos no Mercado Livre.

## v0.4

- Busca de produtos com persistência de snapshots.
- Ranking de mais vendidos por categoria.
- Consulta em lote via /items/bulk.
- Tendências do Mercado Livre.
- Histórico simples de preço e posição.
- Opportunity Radar com score inicial de 0 a 100.
- API FastAPI + dashboard Streamlit.
- PostgreSQL em produção e SQLite como fallback local/teste.

## Rodar

    cp .env.example .env
    pip install -e ".[test]"
    uvicorn market_radar.main:app --reload
    streamlit run dashboard/app.py

## Endpoints

- GET /health
- GET /mercadolivre/search?q=...
- GET /mercadolivre/highlights/{category}
- GET /mercadolivre/trends?category=...
- GET /mercadolivre/opportunities/trending

O histórico é alimentado automaticamente pelas rotas de busca e ranking.

## Próximo passo

Transformar o Opportunity Radar em um ranking comercial: demanda + concorrência + preço + margem estimada + dificuldade logística, e depois conectar sourcing China para calcular custo posto no Brasil.


## Import ranking from Radar

The endpoint `POST /radar/import-ranking/from-radar` converts the products already discovered by the Radar into an import shortlist.

Example request:

```json
{
  "budget": 20000,
  "reserve_pct": 15,
  "radar_limit": 50,
  "sourcing_cost_pct": 30,
  "international_freight_pct": 10,
  "import_tax_pct": 0,
  "listing_type_id": "gold_special",
  "use_ml_fees": true
}
```

The MVP estimates the supplier unit cost and international freight as percentages of the observed Mercado Livre selling price. This is deliberately an estimate until supplier quotations are connected. When `use_ml_fees=true`, the ranking queries Mercado Livre's Listing Prices API and uses the returned `sale_fee_amount` as the marketplace selling cost.

The result is ranked by projected profit, ROI and Radar score, subject to the reserve and minimum-unit constraints.

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

import os
from datetime import timedelta

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from app.domain.models import OrderStatus, now
from app.routers import clientes, config, estoque, loja, pedidos, produtos, vendas
from app.seed import seed
from app.services import core
from app.web import render, uow

app = FastAPI(title="Peças 3D", docs_url="/api/docs", openapi_url="/api/openapi.json")
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")),
          name="static")
for r in (produtos, clientes, estoque, vendas, pedidos, config, loja):
    app.include_router(r.router)

seed(uow)


@app.get("/")
def painel(request: Request):
    hoje = now() - timedelta(hours=24)
    mes = now() - timedelta(days=30)
    with uow:
        vendas = uow.sales.list()
        prods = uow.products.list(lambda p: p.active)
        baixo = [(p, st) for p in prods if (st := core.stock_of(uow, p.id)).quantity <= st.min_quantity]
        pedidos = uow.orders.list(lambda o: o.status not in (OrderStatus.ENTREGUE, OrderStatus.CANCELADO))
        clientes = uow.customers.get_many(o.customer_id for o in pedidos)
        n_clientes = len(uow.customers.list())
    return render(request, "painel.html",
                  vendas_24h=sum((s.total for s in vendas if s.created_at >= hoje), 0),
                  vendas_30d=sum((s.total for s in vendas if s.created_at >= mes), 0),
                  n_vendas=len(vendas), n_produtos=len(prods), n_clientes=n_clientes,
                  baixo=baixo, pedidos=pedidos, clientes=clientes,
                  ultimas=sorted(vendas, key=lambda s: s.id, reverse=True)[:5])


@app.get("/health")
def health():
    return {"ok": True, "backend": os.environ.get("STORAGE_BACKEND", "memory")}

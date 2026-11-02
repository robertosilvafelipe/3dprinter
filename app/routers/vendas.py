from datetime import timedelta

from fastapi import APIRouter, Request

from app.domain.models import PaymentMethod, SaleChannel, now
from app.services import core
from app.web import go, money, render, to_int, uow

router = APIRouter(prefix="/vendas")


@router.get("")
def listar(request: Request, dias: int = 30):
    since = now() - timedelta(days=dias)
    with uow:
        vendas = sorted(uow.sales.list(lambda s: s.created_at >= since),
                        key=lambda s: s.id, reverse=True)
        clientes = uow.customers.get_many(s.customer_id for s in vendas if s.customer_id)
    total = sum((s.total for s in vendas), 0)
    return render(request, "vendas/lista.html", vendas=vendas, clientes=clientes,
                  total=total, dias=dias)


@router.get("/nova")
def nova(request: Request, cliente: int = 0):
    with uow:
        prods = uow.products.list(lambda p: p.active)
        stock = {p.id: core.stock_of(uow, p.id) for p in prods}
        clientes = sorted(uow.customers.list(), key=lambda c: c.name)
    return render(request, "vendas/form.html", produtos=prods, stock=stock,
                  clientes=clientes, cliente=cliente)


@router.post("/salvar")
async def salvar(request: Request):
    f = await request.form()
    try:
        lines = [core.SaleLine(int(k[4:]), to_int(v),
                               money(f.get(f"price_{k[4:]}"), default="") if f.get(f"price_{k[4:]}") else None)
                 for k, v in f.items() if k.startswith("qty_") and to_int(v) > 0]
        sale = core.register_sale(
            uow, to_int(f.get("customer_id")) or None, lines,
            PaymentMethod(f.get("payment_method")), SaleChannel(f.get("channel")),
            money(f.get("discount")), money(f.get("shipping")), str(f.get("notes", "")))
    except (core.BusinessError, ValueError) as e:
        return go("/vendas/nova", err=str(e))
    return go(f"/vendas/{sale.id}", msg="Venda registrada e estoque baixado")


@router.get("/{sid}")
def ver(request: Request, sid: int):
    with uow:
        s = uow.sales.get(sid)
        c = uow.customers.get(s.customer_id) if s and s.customer_id else None
        o = uow.orders.get(s.order_id) if s and s.order_id else None
    if not s:
        return go("/vendas", err="Venda não encontrada")
    return render(request, "vendas/ver.html", s=s, c=c, o=o)

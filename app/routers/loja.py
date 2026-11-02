"""Link público de pedidos: /loja (o cliente final usa, sem login)."""
from fastapi import APIRouter, Request

from app.services import core
from app.services import email as mail
from app.web import go, render, to_int, uow

router = APIRouter(prefix="/loja")


@router.get("")
def vitrine(request: Request):
    with uow:
        s = uow.settings.load()
        prods = uow.products.list(lambda p: p.active)
        cats = {c.id: c for c in uow.categories.list()}
        stock = {p.id: core.stock_of(uow, p.id).quantity for p in prods}
    return render(request, "loja/vitrine.html", produtos=prods, cats=cats, stock=stock,
                  closed=not s.order_link_enabled)


@router.post("/pedido")
async def enviar(request: Request):
    f = await request.form()
    with uow:
        if not uow.settings.load().order_link_enabled:
            return go("/loja", err="Pedidos pelo link estão pausados no momento.")
    name, phone, email = (str(f.get(k, "")).strip() for k in ("name", "phone", "email"))
    if not name or not (phone or email):
        return go("/loja", err="Informe nome e telefone ou e-mail.")
    lines = [core.SaleLine(int(k[4:]), min(to_int(v), 50)) for k, v in f.items()
             if k.startswith("qty_") and to_int(v) > 0]
    try:
        with uow:
            c = core.find_or_create_customer(uow, name, phone, email, str(f.get("city", "")))
            o = core.create_order(uow, c, lines, str(f.get("notes", ""))[:500])
            s = uow.settings.load()
    except core.BusinessError as e:
        return go("/loja", err=str(e))
    mail.notify_order(s.email, s.store_name, o, c)
    return go(f"/loja/pedido/{o.code}", msg="Pedido enviado!")


@router.get("/pedido/{code}")
def acompanhar(request: Request, code: str):
    with uow:
        o = uow.orders.first(lambda o: o.code == code.upper())
    if not o:
        return go("/loja", err="Pedido não encontrado")
    return render(request, "loja/pedido.html", o=o)

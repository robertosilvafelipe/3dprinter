from fastapi import APIRouter, Form, Request

from app.domain.models import MovementType
from app.services import core
from app.web import go, render, to_int, uow

router = APIRouter(prefix="/estoque")


@router.get("")
def painel(request: Request, pid: int = 0):
    with uow:
        prods = uow.products.list()
        stock = {p.id: core.stock_of(uow, p.id) for p in prods}
        movs = sorted(uow.movements.list(lambda m: not pid or m.product_id == pid),
                      key=lambda m: m.id, reverse=True)[:50]
        names = {p.id: p.name for p in prods}
    return render(request, "estoque/painel.html", produtos=prods, stock=stock, movs=movs,
                  names=names, pid=pid)


@router.post("/movimentar")
def movimentar(product_id: int = Form(...), type: MovementType = Form(...),
               quantity: str = Form(...), direction: str = Form("+"), reason: str = Form("")):
    qty = abs(to_int(quantity))
    if type == MovementType.AJUSTE and direction == "-":
        qty = -qty
    if type == MovementType.SAIDA_VENDA:
        return go("/estoque", err="Saída por venda é feita pelo módulo de Vendas")
    try:
        core.move_stock(uow, product_id, qty, type, reason)
    except core.BusinessError as e:
        return go("/estoque", err=str(e))
    return go("/estoque", msg="Movimentação registrada")

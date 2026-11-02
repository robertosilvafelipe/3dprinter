from fastapi import APIRouter, Form, Request

from app.domain.models import OrderStatus, PaymentMethod
from app.services import core
from app.web import go, render, uow

router = APIRouter(prefix="/pedidos")


@router.get("")
def listar(request: Request, status: str = ""):
    with uow:
        pedidos = sorted(uow.orders.list(lambda o: not status or o.status.value == status),
                         key=lambda o: o.id, reverse=True)
        clientes = uow.customers.get_many(o.customer_id for o in pedidos)
    return render(request, "pedidos/lista.html", pedidos=pedidos, clientes=clientes,
                  status=status)


@router.get("/{oid}")
def ver(request: Request, oid: int):
    with uow:
        o = uow.orders.get(oid)
        c = uow.customers.get(o.customer_id) if o else None
        stock = {i.product_id: core.stock_of(uow, i.product_id) for i in o.items} if o else {}
    if not o:
        return go("/pedidos", err="Pedido não encontrado")
    return render(request, "pedidos/ver.html", o=o, c=c, stock=stock)


@router.post("/{oid}/status")
def status(oid: int, status: OrderStatus = Form(...)):
    try:
        core.set_order_status(uow, oid, status)
    except core.BusinessError as e:
        return go(f"/pedidos/{oid}", err=str(e))
    return go(f"/pedidos/{oid}", msg="Status atualizado")


@router.post("/{oid}/faturar")
def faturar(oid: int, payment_method: PaymentMethod = Form(...)):
    try:
        sale = core.order_to_sale(uow, oid, payment_method)
    except core.BusinessError as e:
        return go(f"/pedidos/{oid}", err=str(e))
    return go(f"/vendas/{sale.id}", msg="Pedido faturado: venda registrada e estoque baixado")

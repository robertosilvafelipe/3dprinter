from fastapi import APIRouter, Form, Request

from app.domain.models import Customer
from app.web import go, render, uow

router = APIRouter(prefix="/clientes")


@router.get("")
def listar(request: Request, q: str = ""):
    ql = q.lower()
    with uow:
        cs = uow.customers.list(lambda c: not q or ql in (c.name + c.email + c.phone + c.city).lower())
        compras = {c.id: [s for s in uow.sales.list(lambda s, cid=c.id: s.customer_id == cid)]
                   for c in cs}
    return render(request, "clientes/lista.html", clientes=cs, q=q, compras=compras)


@router.get("/novo")
def novo(request: Request):
    return render(request, "clientes/form.html", c=None, vendas=[], pedidos=[])


@router.get("/{cid}")
def ver(request: Request, cid: int):
    with uow:
        c = uow.customers.get(cid)
        vendas = uow.sales.list(lambda s: s.customer_id == cid)
        pedidos = uow.orders.list(lambda o: o.customer_id == cid)
    if not c:
        return go("/clientes", err="Cliente não encontrado")
    return render(request, "clientes/form.html", c=c, vendas=vendas, pedidos=pedidos)


@router.post("/salvar")
def salvar(cid: int = Form(0), name: str = Form(...), phone: str = Form(""),
           email: str = Form(""), document: str = Form(""), city: str = Form(""),
           state: str = Form(""), notes: str = Form("")):
    data = dict(name=name.strip(), phone=phone.strip(), email=email.strip().lower(),
                document=document.strip(), city=city.strip(), state=state.strip().upper()[:2],
                notes=notes)
    with uow:
        if cid:
            c = uow.customers.get(cid)
            for k, v in data.items():
                setattr(c, k, v)
            uow.customers.update(c)
        else:
            c = uow.customers.add(Customer(**data))
    return go(f"/clientes/{c.id}", msg="Cliente salvo")

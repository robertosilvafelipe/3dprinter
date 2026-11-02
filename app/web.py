"""Infra compartilhada das rotas: templates, prefixo de URL, mensagens."""
import os
from decimal import Decimal, InvalidOperation
from urllib.parse import quote

from fastapi import Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.domain.models import (MovementType, OrderStatus, PaymentMethod, SaleChannel)
from app.repositories.memory import MemoryUnitOfWork

BASE = os.environ.get("BASE_PATH", "").rstrip("/")
BACKEND = os.environ.get("STORAGE_BACKEND", "memory")

if BACKEND != "memory":
    raise RuntimeError(f"STORAGE_BACKEND={BACKEND} ainda não implementado (fase 2)")
uow = MemoryUnitOfWork()

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

LABELS = {
    **{m.value: l for m, l in zip(PaymentMethod, ["Pix", "Dinheiro", "Cartão de crédito",
                                                  "Cartão de débito", "Transferência"])},
    **{c.value: l for c, l in zip(SaleChannel, ["Balcão", "Instagram", "WhatsApp", "Feira",
                                                 "Link de pedidos"])},
    **{s.value: l for s, l in zip(OrderStatus, ["Novo", "Confirmado", "Em produção", "Pronto",
                                                 "Entregue", "Cancelado"])},
    **{t.value: l for t, l in zip(MovementType, ["Entrada", "Saída (venda)", "Ajuste", "Reserva"])},
    "articulado": "Articulado", "fixo": "Fixo",
}


def brl(v) -> str:
    s = f"{Decimal(v or 0):,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def label(v) -> str:
    v = getattr(v, "value", v)
    return LABELS.get(v, v)


def localdt(d) -> str:
    from zoneinfo import ZoneInfo
    return d.astimezone(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M")


templates.env.filters.update(brl=brl, label=label, dt=localdt)
templates.env.globals.update(base=BASE, PaymentMethod=PaymentMethod, SaleChannel=SaleChannel,
                             OrderStatus=OrderStatus, MovementType=MovementType)


def render(request: Request, name: str, **ctx):
    ctx.setdefault("msg", request.query_params.get("msg"))
    ctx.setdefault("err", request.query_params.get("err"))
    with uow:
        ctx.setdefault("store", uow.settings.load())
        ctx.setdefault("new_orders", len(uow.orders.list(lambda o: o.status == OrderStatus.NOVO)))
    return templates.TemplateResponse(request, name, ctx)


def go(path: str, msg: str | None = None, err: str | None = None) -> RedirectResponse:
    path, _, frag = path.partition("#")
    url = BASE + path
    for k, v in (("msg", msg), ("err", err)):
        if v:
            url += ("&" if "?" in url else "?") + f"{k}=" + quote(v)
    return RedirectResponse(url + (f"#{frag}" if frag else ""), status_code=303)


def money(s: str | None, default: str = "0") -> Decimal:
    s = (s or "").strip().replace("R$", "").strip() or default
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return Decimal(s).quantize(Decimal("0.01"))
    except InvalidOperation:
        raise ValueError(f"Valor inválido: {s}")


def to_int(s: str | None, default: int = 0) -> int:
    try:
        return int((s or "").strip() or default)
    except ValueError:
        return default

"""Regras de negócio. Rotas chamam só isto; nada aqui sabe de HTTP."""
from __future__ import annotations

import secrets
from dataclasses import dataclass
from decimal import Decimal

from app.domain.models import (Customer, MovementType, Order, OrderItem, OrderStatus,
                               PaymentMethod, Product, Sale, SaleChannel, SaleItem,
                               StockItem, StockMovement, now)
from app.repositories.base import UnitOfWork


class BusinessError(Exception):
    """Erro de regra de negócio (mostrado ao usuário)."""


# ---------- produtos ----------

def create_product(uow: UnitOfWork, product: Product, initial_qty: int = 0,
                   min_qty: int = 0) -> Product:
    with uow:
        if uow.products.first(lambda p: p.sku.lower() == product.sku.lower()):
            raise BusinessError(f"SKU {product.sku} já existe.")
        if not uow.categories.get(product.category_id):
            raise BusinessError("Categoria inválida.")
        uow.products.add(product)
        uow.stock.add(StockItem(product_id=product.id, quantity=0, min_quantity=min_qty))
        if initial_qty:
            move_stock(uow, product.id, initial_qty, MovementType.ENTRADA, "Estoque inicial")
        return product


def stock_of(uow: UnitOfWork, product_id: int) -> StockItem:
    item = uow.stock.first(lambda s: s.product_id == product_id)
    if item is None:
        item = uow.stock.add(StockItem(product_id=product_id))
    return item


# ---------- estoque ----------

def move_stock(uow: UnitOfWork, product_id: int, qty: int, type: MovementType,
               reason: str = "", sale_id: int | None = None) -> StockMovement:
    with uow:
        if qty == 0:
            raise BusinessError("Quantidade não pode ser zero.")
        item = stock_of(uow, product_id)
        if item.quantity + qty < 0:
            p = uow.products.get(product_id)
            raise BusinessError(
                f"Estoque insuficiente de {p.name if p else product_id}: "
                f"tem {item.quantity}, precisa de {-qty}.")
        item.quantity += qty
        uow.stock.update(item)
        return uow.movements.add(StockMovement(product_id=product_id, type=type,
                                               quantity=qty, reason=reason, sale_id=sale_id))


# ---------- vendas ----------

@dataclass
class SaleLine:
    product_id: int
    quantity: int
    unit_price: Decimal | None = None   # None = preço de tabela


def register_sale(uow: UnitOfWork, customer_id: int | None, lines: list[SaleLine],
                  payment: PaymentMethod, channel: SaleChannel,
                  discount: Decimal = Decimal("0"), shipping: Decimal = Decimal("0"),
                  notes: str = "", order_id: int | None = None) -> Sale:
    lines = [l for l in lines if l.quantity > 0]
    if not lines:
        raise BusinessError("Informe pelo menos um item com quantidade.")
    with uow:
        if customer_id is not None and not uow.customers.get(customer_id):
            raise BusinessError("Cliente não encontrado.")
        items = []
        for l in lines:
            p = uow.products.get(l.product_id)
            if not p:
                raise BusinessError(f"Produto {l.product_id} não existe.")
            items.append(SaleItem(product_id=p.id, quantity=l.quantity,
                                  unit_price=l.unit_price if l.unit_price is not None else p.price,
                                  product_name=p.name))
        sale = Sale(customer_id=customer_id, items=items, payment_method=payment,
                    channel=channel, discount=discount, shipping=shipping,
                    notes=notes, order_id=order_id)
        if sale.total < 0:
            raise BusinessError("Desconto maior que o valor da venda.")
        uow.sales.add(sale)
        for it in items:  # baixa de estoque; se faltar, o UoW desfaz a venda inteira
            move_stock(uow, it.product_id, -it.quantity, MovementType.SAIDA_VENDA,
                       f"Venda #{sale.id}", sale_id=sale.id)
        return sale


# ---------- clientes ----------

def find_or_create_customer(uow: UnitOfWork, name: str, phone: str, email: str,
                            city: str = "") -> Customer:
    with uow:
        email_n, phone_n = email.strip().lower(), _digits(phone)
        found = uow.customers.first(
            lambda c: (email_n and c.email.lower() == email_n)
            or (phone_n and _digits(c.phone) == phone_n))
        if found:
            return found
        return uow.customers.add(Customer(name=name.strip(), phone=phone.strip(),
                                          email=email.strip(), city=city.strip()))


def _digits(s: str) -> str:
    return "".join(ch for ch in s if ch.isdigit())


# ---------- pedidos (link público) ----------

def create_order(uow: UnitOfWork, customer: Customer, lines: list[SaleLine],
                 notes: str = "") -> Order:
    lines = [l for l in lines if l.quantity > 0]
    if not lines:
        raise BusinessError("Escolha pelo menos uma peça.")
    with uow:
        items = []
        for l in lines:
            p = uow.products.get(l.product_id)
            if not p or not p.active:
                raise BusinessError("Produto indisponível.")
            items.append(OrderItem(product_id=p.id, quantity=l.quantity,
                                   unit_price=p.price, product_name=p.name))
        code = _new_code(uow)
        return uow.orders.add(Order(code=code, customer_id=customer.id, items=items, notes=notes))


def _new_code(uow: UnitOfWork) -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    while True:
        code = "P3D-" + "".join(secrets.choice(alphabet) for _ in range(5))
        if not uow.orders.first(lambda o: o.code == code):
            return code


def set_order_status(uow: UnitOfWork, order_id: int, status: OrderStatus) -> Order:
    with uow:
        o = uow.orders.get(order_id)
        if not o:
            raise BusinessError("Pedido não encontrado.")
        if o.sale_id and status == OrderStatus.CANCELADO:
            raise BusinessError("Pedido já virou venda; cancele/estorne a venda primeiro.")
        o.status, o.updated_at = status, now()
        return uow.orders.update(o)


def order_to_sale(uow: UnitOfWork, order_id: int, payment: PaymentMethod) -> Sale:
    with uow:
        o = uow.orders.get(order_id)
        if not o:
            raise BusinessError("Pedido não encontrado.")
        if o.sale_id:
            raise BusinessError("Este pedido já foi faturado.")
        if o.status == OrderStatus.CANCELADO:
            raise BusinessError("Pedido cancelado.")
        sale = register_sale(uow, o.customer_id,
                             [SaleLine(i.product_id, i.quantity, i.unit_price) for i in o.items],
                             payment, SaleChannel.LINK_PEDIDOS,
                             notes=f"Pedido {o.code}", order_id=o.id)
        o.sale_id = sale.id
        if o.status in (OrderStatus.NOVO, OrderStatus.CONFIRMADO):
            o.status = OrderStatus.CONFIRMADO
        o.updated_at = now()
        uow.orders.update(o)
        return sale

"""Entidades de domínio.

Cada dataclass aqui corresponde a uma tabela da versão final (Postgres).
Os nomes de campos já são os nomes de coluna planejados; `id` é a PK.
Dinheiro em Decimal (vira NUMERIC(10,2)), datas em datetime com fuso.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum


def now() -> datetime:
    return datetime.now(timezone.utc)


class ProductKind(str, Enum):
    ARTICULADO = "articulado"
    FIXO = "fixo"


class PaymentMethod(str, Enum):
    PIX = "pix"
    DINHEIRO = "dinheiro"
    CARTAO_CREDITO = "cartao_credito"
    CARTAO_DEBITO = "cartao_debito"
    TRANSFERENCIA = "transferencia"


class SaleChannel(str, Enum):
    BALCAO = "balcao"
    INSTAGRAM = "instagram"
    WHATSAPP = "whatsapp"
    FEIRA = "feira"
    LINK_PEDIDOS = "link_pedidos"


class OrderStatus(str, Enum):
    NOVO = "novo"
    CONFIRMADO = "confirmado"
    EM_PRODUCAO = "em_producao"
    PRONTO = "pronto"
    ENTREGUE = "entregue"
    CANCELADO = "cancelado"


class MovementType(str, Enum):
    ENTRADA = "entrada"        # peça impressa / reposição
    SAIDA_VENDA = "saida_venda"
    AJUSTE = "ajuste"          # inventário, perda, falha de impressão
    RESERVA = "reserva"        # reservado para pedido (futuro)


@dataclass
class Category:                     # tabela categories
    name: str
    kind: ProductKind
    description: str = ""
    id: int | None = None


@dataclass
class Product:                      # tabela products
    sku: str
    name: str
    category_id: int
    price: Decimal
    cost: Decimal = Decimal("0")
    description: str = ""
    material: str = "PLA"
    color: str = ""
    print_time_min: int = 0          # tempo de impressão estimado
    weight_g: int = 0                # filamento gasto
    dimensions: str = ""             # ex.: "18 x 6 x 4 cm"
    stl_url: str = ""                # link do arquivo 3D (futuro: storage)
    image_url: str = ""
    active: bool = True
    created_at: datetime = field(default_factory=now)
    id: int | None = None

    @property
    def margin(self) -> Decimal:
        if not self.price:
            return Decimal("0")
        return ((self.price - self.cost) / self.price * 100).quantize(Decimal("0.1"))


@dataclass
class StockItem:                    # tabela stock_items (1:1 com products)
    product_id: int
    quantity: int = 0
    min_quantity: int = 0
    location: str = ""               # prateleira / caixa
    id: int | None = None


@dataclass
class StockMovement:                # tabela stock_movements
    product_id: int
    type: MovementType
    quantity: int                    # positivo entra, negativo sai
    reason: str = ""
    sale_id: int | None = None
    created_at: datetime = field(default_factory=now)
    id: int | None = None


@dataclass
class Customer:                     # tabela customers
    name: str
    phone: str = ""
    email: str = ""
    document: str = ""               # CPF/CNPJ (opcional)
    city: str = ""
    state: str = ""
    notes: str = ""
    created_at: datetime = field(default_factory=now)
    id: int | None = None


@dataclass
class SaleItem:                     # tabela sale_items
    product_id: int
    quantity: int
    unit_price: Decimal
    product_name: str = ""           # snapshot do nome no momento da venda

    @property
    def total(self) -> Decimal:
        return self.unit_price * self.quantity


@dataclass
class Sale:                         # tabela sales
    customer_id: int | None
    items: list[SaleItem]
    payment_method: PaymentMethod
    channel: SaleChannel = SaleChannel.BALCAO
    discount: Decimal = Decimal("0")
    shipping: Decimal = Decimal("0")
    notes: str = ""
    order_id: int | None = None
    created_at: datetime = field(default_factory=now)
    id: int | None = None

    @property
    def subtotal(self) -> Decimal:
        return sum((i.total for i in self.items), Decimal("0"))

    @property
    def total(self) -> Decimal:
        return self.subtotal - self.discount + self.shipping


@dataclass
class OrderItem:                    # tabela order_items
    product_id: int
    quantity: int
    unit_price: Decimal
    product_name: str = ""
    customization: str = ""          # cor/nome gravado etc.

    @property
    def total(self) -> Decimal:
        return self.unit_price * self.quantity


@dataclass
class Order:                        # tabela orders (pedidos vindos do link público)
    code: str                        # código curto público, ex.: P3D-4F7K
    customer_id: int
    items: list[OrderItem]
    status: OrderStatus = OrderStatus.NOVO
    notes: str = ""
    sale_id: int | None = None
    created_at: datetime = field(default_factory=now)
    updated_at: datetime = field(default_factory=now)
    id: int | None = None

    @property
    def total(self) -> Decimal:
        return sum((i.total for i in self.items), Decimal("0"))


@dataclass
class EmailSettings:
    enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""          # futuro: cifrado / variável de ambiente
    use_tls: bool = True
    from_name: str = "Peças 3D"
    from_email: str = ""
    notify_email: str = ""           # quem recebe aviso de pedido novo
    notify_new_order: bool = True
    send_order_confirmation: bool = True   # e-mail para o cliente


@dataclass
class StoreSettings:                # tabela settings (linha única / chave-valor)
    store_name: str = "Peças 3D"
    whatsapp: str = ""
    instagram: str = ""
    order_link_enabled: bool = True
    order_link_message: str = "Escolha suas peças e enviamos a confirmação por e-mail."
    email: EmailSettings = field(default_factory=EmailSettings)

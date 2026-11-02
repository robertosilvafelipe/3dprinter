"""Dados iniciais (carregados a cada boot enquanto não há banco)."""
from decimal import Decimal as D

from app.domain.models import (Category, Customer, MovementType, PaymentMethod, Product,
                               ProductKind, SaleChannel)
from app.repositories.base import UnitOfWork
from app.services import core


def seed(uow: UnitOfWork) -> None:
    with uow:
        art = uow.categories.add(Category("Articulados", ProductKind.ARTICULADO,
                                          "Peças com juntas móveis impressas no lugar"))
        fixo = uow.categories.add(Category("Fixo", ProductKind.FIXO,
                                           "Peças rígidas, utilitárias e decorativas"))

        P = core.create_product
        dragao = P(uow, Product("ART-DRG-01", "Dragão articulado", art.id, D("89.90"), D("18.50"),
                               "Dragão com corpo segmentado e asas articuladas.", "PLA silk",
                               "Dourado/roxo", 540, 140, "30 x 12 x 6 cm"), 6, 2)
        cobra = P(uow, Product("ART-CBR-01", "Cobra articulada", art.id, D("39.90"), D("6.20"),
                              "Cobra flexível de 40 segmentos.", "PLA", "Verde", 210, 48,
                              "45 x 3 x 2 cm"), 12, 4)
        suporte = P(uow, Product("FIX-SUP-01", "Suporte de celular", fixo.id, D("29.90"), D("4.10"),
                                "Suporte de mesa com ângulo de 60°, cabe celular com capa.",
                                "PETG", "Preto", 150, 35, "9 x 8 x 11 cm"), 15, 5)
        chaveiro = P(uow, Product("FIX-CHV-01", "Chaveiro", fixo.id, D("9.90"), D("0.80"),
                                 "Chaveiro com argola, personalizável com nome.", "PLA",
                                 "Diversas", 25, 6, "5 x 3 x 0,4 cm"), 40, 10)

        ana = uow.customers.add(Customer("Ana Souza", "(11) 98888-1111",
                                              "ana@example.com", city="São Paulo", state="SP"))
        uow.customers.add(Customer("Bruno Lima", "(21) 97777-2222", "bruno@example.com",
                                        city="Rio de Janeiro", state="RJ",
                                        notes="Prefere retirar pessoalmente"))
        carla = uow.customers.add(Customer("Carla Mendes", "(31) 96666-3333",
                                                "carla@example.com", city="Belo Horizonte",
                                                state="MG"))

        core.register_sale(uow, ana.id, [core.SaleLine(dragao.id, 1), core.SaleLine(chaveiro.id, 2)],
                           PaymentMethod.PIX, SaleChannel.INSTAGRAM)
        core.register_sale(uow, None, [core.SaleLine(chaveiro.id, 5)], PaymentMethod.DINHEIRO,
                           SaleChannel.FEIRA, discount=D("4.50"))
        core.move_stock(uow, cobra.id, -1, MovementType.AJUSTE, "Falha de impressão")
        core.create_order(uow, carla, [core.SaleLine(cobra.id, 2), core.SaleLine(suporte.id, 1)],
                          "Cobra em azul, se possível")

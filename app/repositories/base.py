"""Contratos de repositório.

Os serviços e rotas só conhecem estas interfaces. Hoje a implementação é
em memória (memory.py); na fase 2 entra uma implementação SQLAlchemy
(postgres.py) com a mesma assinatura, escolhida por STORAGE_BACKEND.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, Generic, Iterable, TypeVar

from app.domain.models import StoreSettings

T = TypeVar("T")


class Repository(ABC, Generic[T]):
    @abstractmethod
    def add(self, entity: T) -> T: ...

    @abstractmethod
    def get(self, id: int) -> T | None: ...

    @abstractmethod
    def list(self, where: Callable[[T], bool] | None = None) -> list[T]: ...

    @abstractmethod
    def update(self, entity: T) -> T: ...

    @abstractmethod
    def delete(self, id: int) -> None: ...

    def first(self, where: Callable[[T], bool]) -> T | None:
        return next(iter(self.list(where)), None)

    def get_many(self, ids: Iterable[int]) -> dict[int, T]:
        return {i: e for i in set(ids) if (e := self.get(i)) is not None}


class SettingsRepository(ABC):
    @abstractmethod
    def load(self) -> StoreSettings: ...

    @abstractmethod
    def save(self, settings: StoreSettings) -> None: ...


class UnitOfWork(ABC):
    """Agrupa os repositórios. No Postgres vira sessão + transação."""

    categories: Repository
    products: Repository
    stock: Repository
    movements: Repository
    customers: Repository
    sales: Repository
    orders: Repository
    settings: SettingsRepository

    @abstractmethod
    def __enter__(self) -> "UnitOfWork": ...

    @abstractmethod
    def __exit__(self, *exc) -> None: ...

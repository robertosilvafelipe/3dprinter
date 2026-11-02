"""Implementação em memória (MVP). Some ao reiniciar o container."""
from __future__ import annotations

import copy
import threading
from typing import Callable, Generic, TypeVar

from app.domain.models import StoreSettings
from app.repositories.base import Repository, SettingsRepository, UnitOfWork

T = TypeVar("T")


class MemoryRepository(Repository[T], Generic[T]):
    def __init__(self) -> None:
        self._rows: dict[int, T] = {}
        self._seq = 0

    def add(self, entity: T) -> T:
        self._seq += 1
        entity.id = self._seq  # type: ignore[attr-defined]
        self._rows[self._seq] = entity
        return entity

    def get(self, id: int) -> T | None:
        return self._rows.get(id)

    def list(self, where: Callable[[T], bool] | None = None) -> list[T]:
        rows = list(self._rows.values())
        return [r for r in rows if where(r)] if where else rows

    def update(self, entity: T) -> T:
        if entity.id not in self._rows:  # type: ignore[attr-defined]
            raise KeyError(entity.id)  # type: ignore[attr-defined]
        self._rows[entity.id] = entity  # type: ignore[attr-defined]
        return entity

    def delete(self, id: int) -> None:
        self._rows.pop(id, None)


class MemorySettingsRepository(SettingsRepository):
    def __init__(self) -> None:
        self._settings = StoreSettings()

    def load(self) -> StoreSettings:
        return copy.deepcopy(self._settings)

    def save(self, settings: StoreSettings) -> None:
        self._settings = copy.deepcopy(settings)


class MemoryUnitOfWork(UnitOfWork):
    """Lock global + snapshot: se der exceção dentro do `with`, desfaz tudo
    (mesma semântica de rollback que a versão com banco terá)."""

    _NAMES = ("categories", "products", "stock", "movements",
              "customers", "sales", "orders", "settings")

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._depth = 0
        self._snapshot: dict | None = None
        self.categories = MemoryRepository()
        self.products = MemoryRepository()
        self.stock = MemoryRepository()
        self.movements = MemoryRepository()
        self.customers = MemoryRepository()
        self.sales = MemoryRepository()
        self.orders = MemoryRepository()
        self.settings = MemorySettingsRepository()

    def __enter__(self) -> "MemoryUnitOfWork":
        self._lock.acquire()
        if self._depth == 0:
            self._snapshot = {n: copy.deepcopy(getattr(self, n).__dict__) for n in self._NAMES}
        self._depth += 1
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            self._depth -= 1
            if self._depth == 0:
                if exc_type is not None and self._snapshot is not None:
                    for n, state in self._snapshot.items():
                        getattr(self, n).__dict__.update(state)
                self._snapshot = None
        finally:
            self._lock.release()

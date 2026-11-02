"""Smoke test: abre todas as telas e exercita os fluxos principais.
Rodar da raiz: PYTHONPATH=. python tests/smoke.py"""
import os, re
os.environ["BASE_PATH"] = "/pecas3d"
from fastapi.testclient import TestClient
from app.main import app
c = TestClient(app, follow_redirects=False)
for p in ["/", "/produtos", "/produtos/novo", "/produtos/1", "/clientes", "/clientes/1", "/clientes/novo",
          "/estoque", "/estoque?pid=2", "/vendas", "/vendas/nova", "/vendas/1", "/pedidos", "/pedidos/1",
          "/config", "/loja", "/health", "/api/docs"]:
    r = c.get(p); assert r.status_code == 200, (p, r.status_code, r.text[:500]); print("OK", p)
# novo produto
r = c.post("/produtos/salvar", data=dict(sku="art-pol-01", name="Polvo articulado", category_id="1", price="49,90", cost="7,5", initial_qty="3", min_qty="1"))
print("novo produto ->", r.headers["location"])
# venda de chaveiros acima do estoque deve falhar e não baixar nada
r = c.post("/vendas/salvar", data={"qty_4": "999", "qty_1": "1", "payment_method": "pix", "channel": "balcao", "customer_id": "0"})
print("venda excessiva ->", r.headers["location"])
assert "Estoque insuficiente" in __import__("urllib.parse").parse.unquote(r.headers["location"])
from app.web import uow
from app.services.core import stock_of
print("dragão estoque após rollback:", stock_of(uow, 1).quantity)
r = c.post("/vendas/salvar", data={"qty_5": "2", "price_5": "45", "payment_method": "pix", "channel": "whatsapp", "customer_id": "2", "discount": "5"})
print("venda ok ->", r.headers["location"]); assert c.get(r.headers["location"].replace("/pecas3d","")).status_code == 200
# pedido público
r = c.post("/loja/pedido", data={"name": "Diego", "phone": "11 95555-0000", "email": "d@x.com", "qty_1": "1", "notes": "verde"})
loc = r.headers["location"]; print("pedido ->", loc)
code = re.search(r"P3D-\w+", loc).group(0)
assert c.get(f"/loja/pedido/{code}").status_code == 200
oid = [o for o in uow.orders.list() if o.code == code][0].id
r = c.post(f"/pedidos/{oid}/faturar", data={"payment_method": "pix"}); print("faturar ->", r.headers["location"])
r = c.post(f"/pedidos/{oid}/faturar", data={"payment_method": "pix"}); print("faturar 2x ->", r.headers["location"])
r = c.post("/estoque/movimentar", data={"product_id": "2", "type": "ajuste", "direction": "-", "quantity": "1", "reason": "teste"}); print("ajuste ->", r.headers["location"])
r = c.post("/config/email/teste", data={"to": "a@b.com"}); print("teste email ->", r.headers["location"])
r = c.post("/clientes/salvar", data={"name": "Eva", "state": "sp"}); print("cliente ->", r.headers["location"])
for p in ["/", "/pedidos", "/vendas", "/clientes", "/estoque"]:
    assert c.get(p).status_code == 200
print("ALL OK")

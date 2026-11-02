# Peças 3D — gestão de vendas (MVP)

Sistema de vendas de peças impressas em 3D. MVP **sem banco**: tudo em memória,
recarregado com os dados de exemplo a cada reinício do container.

## Rodar
```bash
docker compose up -d --build      # sobe em 127.0.0.1:8010
```
No oracle-dr o nginx publica em `http://<ip>/pecas3d/` (ver `deploy/nginx-pecas3d.conf`).
Link público de pedidos (para clientes): `/pecas3d/loja`.

## Módulos
| Módulo | Rota | O que faz |
|---|---|---|
| Painel | `/` | KPIs, pedidos em aberto, estoque baixo, link de pedidos |
| Produtos | `/produtos` | cadastro de peça 3D (SKU, categoria, material, tempo de impressão, filamento, custo/preço/margem, STL) e categorias |
| Estoque | `/estoque` | posição, mínimo, entradas/ajustes, histórico de movimentações |
| Vendas | `/vendas` | registro de venda com itens, desconto, frete, canal, pagamento; baixa estoque (tudo ou nada) |
| Pedidos | `/pedidos` | pedidos vindos do link público; status e "faturar" (vira venda) |
| Clientes | `/clientes` | cadastro básico + histórico de compras/pedidos |
| Configurações | `/config` | dados da loja, abrir/pausar link, SMTP (teste de envio), avisos por e-mail |
| Loja pública | `/loja` | vitrine + formulário de pedido + acompanhamento `/loja/pedido/{código}` |

## Arquitetura (pensada para a versão final)
```
app/
  domain/models.py         entidades = tabelas futuras (categories, products, stock_items,
                           stock_movements, customers, sales, sale_items, orders, order_items, settings)
  repositories/base.py     contratos Repository / UnitOfWork
  repositories/memory.py   implementação atual (lock + snapshot = rollback)
  services/core.py         regras de negócio (venda, estoque, pedido→venda)
  services/email.py        SMTP
  routers/                 uma rota por módulo (HTML server-side, Jinja2)
```
Rotas nunca acessam dados direto: chamam `services` com um `UnitOfWork`.

## Documentação
- [docs/ARQUITETURA.md](docs/ARQUITETURA.md) — camadas, modelo de dados, regras
- [docs/INFRA.md](docs/INFRA.md) — servidor, Docker, nginx, deploy
- [docs/ROADMAP.md](docs/ROADMAP.md) — fases
- [CLAUDE.md](CLAUDE.md) — resumo rápido para o Claude

Teste: `PYTHONPATH=. python tests/smoke.py`

## Próximas fases
1. **Persistência**: `repositories/postgres.py` (SQLAlchemy 2 + Alembic), serviço `db` no
   compose (já comentado), `STORAGE_BACKEND=postgres`. Nada em `services/` ou `routers/` muda.
2. **Login** (admin/vendedor) — hoje o painel está aberto, só a `/loja` deveria ser pública.
3. Fotos dos produtos (upload), envio de e-mail em fila, WhatsApp, Pix no link de pedidos.
4. HTTPS + domínio.

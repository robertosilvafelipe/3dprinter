# Arquitetura

## Visão geral
Aplicação web server-side (FastAPI + Jinja2), sem build de front-end. Uma única
imagem Docker, um único processo. O MVP guarda tudo em memória; a estrutura já
separa as camadas para trocar o armazenamento por Postgres sem mexer em telas
nem em regras de negócio.

```
 navegador ──HTTP──▶ nginx (host) ──/pecas3d/──▶ container pecas3d-web :8000
                                                   │
                                     routers/  (HTTP, formulários, templates)
                                                   │ chama
                                     services/ (regras: venda, estoque, pedido)
                                                   │ usa
                                     repositories/base.py  (contratos)
                                          │                      │
                               memory.py (MVP, hoje)    postgres.py (fase 2)
```

## Camadas
| Pasta | Responsabilidade | Regra |
|---|---|---|
| `app/domain/models.py` | Entidades (dataclasses) e enums | Cada classe = uma tabela futura; nomes de campo = nomes de coluna |
| `app/repositories/base.py` | `Repository[T]`, `SettingsRepository`, `UnitOfWork` | Única porta de acesso a dados |
| `app/repositories/memory.py` | Implementação em memória | Lock global + snapshot: exceção dentro do `with uow` desfaz tudo (simula transação) |
| `app/services/core.py` | Regras de negócio | Não conhece HTTP; levanta `BusinessError` com mensagem para o usuário |
| `app/services/email.py` | Envio SMTP e avisos de pedido | Falha de e-mail nunca derruba o pedido |
| `app/routers/*.py` | Uma rota por módulo | Só traduz formulário → serviço → redirect/template |
| `app/web.py` | Templates, filtros (`brl`, `label`, `dt`), `BASE_PATH`, `uow` global | Escolhe backend via `STORAGE_BACKEND` |
| `app/seed.py` | Dados de exemplo carregados no boot | Some quando houver banco (vira migration/fixture opcional) |

## Modelo de dados (tabelas planejadas)
```
categories (id, name, kind[articulado|fixo], description)
products (id, sku UNIQUE, name, category_id→categories, price, cost, description,
          material, color, print_time_min, weight_g, dimensions, stl_url, image_url,
          active, created_at)
stock_items (id, product_id UNIQUE→products, quantity, min_quantity, location)
stock_movements (id, product_id→products, type[entrada|saida_venda|ajuste|reserva],
                 quantity(±), reason, sale_id→sales NULL, created_at)
customers (id, name, phone, email, document, city, state, notes, created_at)
sales (id, customer_id→customers NULL, payment_method, channel, discount, shipping,
       notes, order_id→orders NULL, created_at)
sale_items (sale_id→sales, product_id→products, quantity, unit_price, product_name)
orders (id, code UNIQUE "P3D-XXXXX", customer_id→customers, status, notes,
        sale_id→sales NULL, created_at, updated_at)
order_items (order_id→orders, product_id→products, quantity, unit_price,
             product_name, customization)
settings (linha única ou chave/valor: loja + e-mail)
```
- Dinheiro: `Decimal` → `NUMERIC(10,2)`. Datas: UTC com fuso; exibição em America/Sao_Paulo.
- `sale_items.product_name` / `order_items.product_name`: cópia do nome no momento da venda
  (histórico não muda se o produto for renomeado).
- Estoque: `stock_items.quantity` é o saldo; `stock_movements` é o razão (auditoria).
  Toda alteração de saldo passa por `services.core.move_stock`.

## Regras de negócio já implementadas
- Venda com vários itens baixa o estoque de todos; se faltar qualquer um, nada é gravado.
- Preço cobrado pode diferir do preço de tabela (campo opcional por item).
- Desconto não pode deixar o total negativo.
- Pedido do link público: cliente é reaproveitado por e-mail ou telefone (só dígitos).
- Pedido → venda ("faturar") só uma vez; pedido faturado não pode ser cancelado.
- "Saída por venda" não pode ser lançada manualmente no estoque.

## Rotas
| Rota | Público? | Descrição |
|---|---|---|
| `/` | não* | Painel |
| `/produtos`, `/produtos/novo`, `/produtos/{id}` | não* | Cadastro de peças e categorias |
| `/estoque` | não* | Saldo, movimentações |
| `/vendas`, `/vendas/nova`, `/vendas/{id}` | não* | Registro de vendas |
| `/pedidos`, `/pedidos/{id}` | não* | Pedidos do link; status; faturar |
| `/clientes`, `/clientes/{id}` | não* | Cadastro de clientes |
| `/config` | não* | Loja, link de pedidos, SMTP |
| `/loja`, `/loja/pedido/{code}` | **sim** | Vitrine e acompanhamento |
| `/health`, `/api/docs` | — | Saúde e OpenAPI |

\* Ainda **sem login** no MVP — ver ROADMAP.

## Por que estas escolhas
- **Sem SPA/Node**: servidor tem 764 MB de RAM e já roda outro sistema; HTML server-side é leve.
- **1 worker uvicorn**: obrigatório enquanto o estado é em memória (vários workers = dados divergentes).
- **`BASE_PATH`**: o app roda atrás de um prefixo (`/pecas3d`) no nginx compartilhado;
  todos os links e redirects usam `{{ base }}` / `web.go()`.

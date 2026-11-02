# Roadmap

## Fase 1 — MVP (feito, 02/11/2026)
- [x] Produtos 3D + categorias (Articulados: dragão, cobra; Fixo: suporte de celular, chaveiro)
- [x] Estoque com saldo, mínimo e movimentações
- [x] Vendas com baixa de estoque atômica
- [x] Clientes básicos
- [x] Link público de pedidos (`/loja`) + gestão de pedidos + faturar pedido → venda
- [x] Configurações: loja, pausar link, SMTP com teste, avisos de pedido
- [x] Docker compose + nginx no oracle-dr

## Fase 2 — Segurança e persistência (próximo)
- [ ] **Login** no painel (admin/vendedor); só `/loja` pública. Prioridade: hoje está aberto.
- [ ] `repositories/postgres.py` (SQLAlchemy 2 + Alembic), `STORAGE_BACKEND=postgres`
      — usar o Postgres 16 já existente no host (role/db próprios) **ou** o serviço `db`
      comentado no compose (custa ~100+ MB de RAM; avaliar).
- [ ] Senha SMTP fora do banco em texto puro (variável de ambiente ou cifrada).
- [ ] Backup diário do banco.
- [ ] Testes automatizados (pytest) a partir do smoke test.
- [ ] Domínio + HTTPS (Certbot) — necessário antes de usar login/SMTP de verdade.

## Fase 3 — Operação
- [ ] Upload de fotos dos produtos
- [ ] Variações (cor/tamanho) e personalização (nome no chaveiro) com preço adicional
- [ ] Fila de produção: pedido → impressão (tempo/filamento estimados) → pronto
- [ ] Custo calculado: filamento (R$/kg) + energia + tempo de máquina
- [ ] Estorno/cancelamento de venda com devolução ao estoque
- [ ] Relatórios: mais vendidos, margem por categoria, vendas por canal

## Fase 4 — Integrações
- [ ] E-mail em fila (worker), templates HTML
- [ ] WhatsApp (aviso de pedido)
- [ ] Pix / Mercado Pago no link de pedidos
- [ ] Instagram Shopping / catálogo
- [ ] CI/CD (GitHub Actions → build de imagem → deploy)

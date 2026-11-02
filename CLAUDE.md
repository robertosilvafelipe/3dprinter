# CLAUDE.md — contexto rápido para o Claude

Sistema de vendas de peças impressas em 3D. **Leia isto antes de qualquer mudança.**
Detalhes: `docs/ARQUITETURA.md`, `docs/INFRA.md`, `docs/ROADMAP.md`.

## Estado (02/11/2026)
- MVP no ar: http://129.80.14.146/pecas3d/ (painel) e `/pecas3d/loja` (pedidos públicos).
- FastAPI 0.115 + Jinja2, HTML server-side, **sem banco** (dados em memória, seed a cada boot).
- **Sem login** — painel aberto na internet. Primeira prioridade da fase 2.
- Módulos: produtos, estoque, vendas, pedidos (link público), clientes, configurações/SMTP.

## Onde roda
- Servidor `oracle-dr` (`ssh oracle-dr`, usuário rocky, sudo). Rocky 9, **764 MB RAM**, SELinux.
- Compartilhado com o Dicionário LexWay (nginx, gunicorn :8001, Postgres 16, Redis). Não quebrar.
- `/opt/pecas3d`, `sudo docker compose up -d --build`, container `pecas3d-web` em `127.0.0.1:8010`.
- nginx do host: `include /etc/nginx/conf.d/pecas3d.locations;` dentro de `lexway.conf`.

## Regras do código
- Rotas (`app/routers`) → serviços (`app/services`) → repositórios (`app/repositories/base.py`).
  Rotas nunca mexem em dados direto; toda escrita dentro de `with uow:`.
- Saldo de estoque só muda por `services.core.move_stock` (gera movimentação).
- `app/domain/models.py`: cada dataclass = tabela futura; não renomear campos à toa.
- Links/redirects sempre com prefixo: `{{ base }}` nos templates, `web.go()` nas rotas.
- Nos templates **não usar a variável `p`** no `base.html` (colidiu com produto uma vez).
- 1 worker uvicorn enquanto o backend for memória.
- Erros para o usuário: `raise BusinessError("mensagem")` → redirect com `?err=`.

## Como testar
```bash
python3 -m venv /tmp/v && /tmp/v/bin/pip install -r requirements.txt httpx
PYTHONPATH=. /tmp/v/bin/python tests/smoke.py
```

## Próximo passo sugerido
Login (sessão por cookie, usuário admin) → Postgres (`repositories/postgres.py` + Alembic)
→ domínio/HTTPS. Ver `docs/ROADMAP.md`.

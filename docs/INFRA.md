# Infraestrutura

## Servidor
- **oracle-dr** (Oracle Cloud), IP público `129.80.14.146`, Rocky Linux 9.8, x86_64,
  ~764 MB RAM + 4 GB swap, SELinux enforcing.
- Compartilhado com o Dicionário LexWay (nginx + gunicorn :8001, Postgres 16, Redis) e
  backups do KravManager. **Cuidado com memória e com o nginx compartilhado.**
- Portas públicas controladas pela Security List da OCI (abertas: 22, 80). Não há firewalld.

## Docker
- Docker CE + plugin compose instalados em 02/11/2026 (repo oficial `docker-ce.repo`).
- Código em `/opt/pecas3d` (dono root). Subir/atualizar:
  ```bash
  cd /opt/pecas3d && sudo docker compose up -d --build
  sudo docker compose logs -f web
  ```
- Container `pecas3d-web`: imagem `python:3.12-slim`, usuário não-root, `mem_limit: 160m`
  (uso ~55 MB), porta publicada só em `127.0.0.1:8010`.
- Variáveis: `BASE_PATH=/pecas3d`, `STORAGE_BACKEND=memory`.

## nginx (do host, compartilhado)
- `/etc/nginx/conf.d/lexway.conf` (server do dicionário) recebeu a linha
  `include /etc/nginx/conf.d/pecas3d.locations;` antes de `location /static/`.
- `/etc/nginx/conf.d/pecas3d.locations` = `deploy/nginx-pecas3d.conf` deste repo
  (extensão `.locations` de propósito: `*.conf` em conf.d é incluído no nível `http`).
- Backup do original: `/etc/nginx/lexway.conf.bak-pecas3d`.
- Rollback: remover a linha `include`, `sudo nginx -t && sudo systemctl reload nginx`.
- Sem cache para `/pecas3d/` (o cache do nginx vale só para o `location /` do dicionário).

## Deploy (atual, manual)
Da máquina local:
```bash
cd ~/pecas3d
tar czf - --exclude=__pycache__ --exclude=.git . | ssh oracle-dr \
  'sudo tar xzf - -C /opt/pecas3d && cd /opt/pecas3d && sudo docker compose up -d --build'
```
Reiniciar o container **apaga todos os dados** (MVP em memória).

## Armadilhas do RHEL/Rocky neste servidor
- Arquivos movidos com `mv` de `/tmp` para `/etc/...` herdam contexto SELinux errado;
  escrever direto no destino (`ssh host "sudo tee /destino" < arquivo`).
- `httpd_can_network_connect` já está ligado (nginx → 127.0.0.1:porta funciona).

## URLs
- Painel: http://129.80.14.146/pecas3d/
- Link de pedidos: http://129.80.14.146/pecas3d/loja
- Saúde: http://129.80.14.146/pecas3d/health

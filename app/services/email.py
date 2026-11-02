"""Integração de e-mail via SMTP (Gmail com senha de app, Zoho, SES, etc.).

Envio é síncrono no MVP. Na versão final vai para uma fila/worker
para não segurar a requisição do cliente.
"""
from __future__ import annotations

import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

from app.domain.models import Customer, EmailSettings, Order

log = logging.getLogger("pecas3d.email")


class EmailError(Exception):
    pass


def send(cfg: EmailSettings, to: str, subject: str, body: str) -> None:
    if not (cfg.smtp_host and cfg.from_email):
        raise EmailError("SMTP não configurado (servidor e remetente são obrigatórios).")
    msg = EmailMessage()
    msg["From"] = formataddr((cfg.from_name, cfg.from_email))
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    try:
        if cfg.smtp_port == 465:
            with smtplib.SMTP_SSL(cfg.smtp_host, cfg.smtp_port, timeout=15,
                                  context=ssl.create_default_context()) as s:
                _login_send(s, cfg, msg)
        else:
            with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=15) as s:
                if cfg.use_tls:
                    s.starttls(context=ssl.create_default_context())
                _login_send(s, cfg, msg)
    except (OSError, smtplib.SMTPException) as e:
        raise EmailError(f"Falha no envio: {e}") from e


def _login_send(s: smtplib.SMTP, cfg: EmailSettings, msg: EmailMessage) -> None:
    if cfg.smtp_user:
        s.login(cfg.smtp_user, cfg.smtp_password)
    s.send_message(msg)


def notify_order(cfg: EmailSettings, store_name: str, order: Order, customer: Customer) -> list[str]:
    """Dispara os avisos de pedido novo. Nunca derruba o pedido: devolve erros."""
    if not cfg.enabled:
        return []
    errors: list[str] = []
    lines = "\n".join(f"- {i.quantity}x {i.product_name}  R$ {i.total:.2f}" for i in order.items)
    if cfg.notify_new_order and cfg.notify_email:
        try:
            send(cfg, cfg.notify_email, f"[{store_name}] Pedido novo {order.code}",
                 f"Cliente: {customer.name} ({customer.phone} / {customer.email})\n\n"
                 f"{lines}\n\nTotal: R$ {order.total:.2f}\nObs.: {order.notes or '-'}")
        except EmailError as e:
            errors.append(str(e))
    if cfg.send_order_confirmation and customer.email:
        try:
            send(cfg, customer.email, f"Recebemos seu pedido {order.code} — {store_name}",
                 f"Olá, {customer.name}!\n\nRecebemos seu pedido {order.code}:\n\n{lines}\n\n"
                 f"Total: R$ {order.total:.2f}\n\nEntraremos em contato para confirmar "
                 f"pagamento e prazo.\n\n{store_name}")
        except EmailError as e:
            errors.append(str(e))
    for e in errors:
        log.warning("e-mail do pedido %s: %s", order.code, e)
    return errors

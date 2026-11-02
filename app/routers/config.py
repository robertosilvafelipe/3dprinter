from fastapi import APIRouter, Form, Request

from app.services import email as mail
from app.web import go, render, to_int, uow

router = APIRouter(prefix="/config")


@router.get("")
def tela(request: Request):
    return render(request, "config/tela.html")


@router.post("/loja")
def salvar_loja(store_name: str = Form(...), whatsapp: str = Form(""), instagram: str = Form(""),
                order_link_enabled: str = Form(""), order_link_message: str = Form("")):
    with uow:
        s = uow.settings.load()
        s.store_name, s.whatsapp, s.instagram = store_name.strip(), whatsapp, instagram
        s.order_link_enabled, s.order_link_message = bool(order_link_enabled), order_link_message
        uow.settings.save(s)
    return go("/config", msg="Dados da loja salvos")


@router.post("/email")
def salvar_email(enabled: str = Form(""), smtp_host: str = Form(""), smtp_port: str = Form("587"),
                 smtp_user: str = Form(""), smtp_password: str = Form(""), use_tls: str = Form(""),
                 from_name: str = Form(""), from_email: str = Form(""),
                 notify_email: str = Form(""), notify_new_order: str = Form(""),
                 send_order_confirmation: str = Form("")):
    with uow:
        s = uow.settings.load()
        e = s.email
        e.enabled, e.smtp_host, e.smtp_port = bool(enabled), smtp_host.strip(), to_int(smtp_port, 587)
        e.smtp_user, e.use_tls = smtp_user.strip(), bool(use_tls)
        if smtp_password:            # campo vazio = mantém a senha atual
            e.smtp_password = smtp_password
        e.from_name, e.from_email, e.notify_email = from_name, from_email.strip(), notify_email.strip()
        e.notify_new_order, e.send_order_confirmation = bool(notify_new_order), bool(send_order_confirmation)
        uow.settings.save(s)
    return go("/config#email", msg="Configuração de e-mail salva")


@router.post("/email/teste")
def testar(to: str = Form(...)):
    with uow:
        s = uow.settings.load()
    try:
        mail.send(s.email, to.strip(), f"[{s.store_name}] Teste de e-mail",
                  "Se você recebeu esta mensagem, a integração SMTP está funcionando.")
    except mail.EmailError as e:
        return go("/config#email", err=str(e))
    return go("/config#email", msg=f"E-mail de teste enviado para {to}")

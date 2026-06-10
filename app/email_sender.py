"""Envio do arquivo de resultados do aluno por e-mail ao professor.

O anexo é sempre gerado pelo próprio app (arquivo de resultados com checksum).
O aluno não consegue anexar outros arquivos — evita envio de anexos indevidos.

Configuração (secrets.toml ou Secrets no Streamlit Cloud):

[email]
username = "conta-do-app@gmail.com"     # conta que envia
password = "senha-de-app-do-gmail"      # senha de app (não a senha normal)
professor_email = "professor@gmail.com" # destino (opcional; padrão: admin)
smtp_host = "smtp.gmail.com"            # opcional
smtp_port = 587                          # opcional
"""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from urllib.parse import quote

import streamlit as st

import auth_users


def _email_secrets() -> dict:
    try:
        return dict(st.secrets.get("email", {}))
    except Exception:
        return {}


def professor_email() -> str:
    cfg = _email_secrets()
    dest = (cfg.get("professor_email") or "").strip().lower()
    return dest or (auth_users.get_system_admin_email() or "")


def smtp_configured() -> bool:
    cfg = _email_secrets()
    return bool(cfg.get("username") and cfg.get("password"))


def _build_subject(student_name: str) -> str:
    return f"[Projeto Quiz] Resultados de {student_name}"


def _build_body(student_name: str, student_email: str | None, extra_note: str) -> str:
    lines = [
        "Olá, professor!",
        "",
        "Segue em anexo o arquivo de resultados gerado automaticamente pelo app.",
        "",
        f"Aluno: {student_name}",
    ]
    if student_email:
        lines.append(f"Conta Google: {student_email}")
    if extra_note.strip():
        lines += ["", "Mensagem do aluno:", extra_note.strip()]
    lines += [
        "",
        "Para registrar: painel do professor → aba Resultados → "
        "Importar arquivo de resultados de aluno.",
    ]
    return "\n".join(lines)


def send_results_email(
    *,
    student_name: str,
    student_email: str | None,
    file_bytes: bytes,
    filename: str,
    extra_note: str = "",
) -> str | None:
    """Envia o e-mail com o anexo gerado pelo app. Retorna mensagem de erro ou None."""
    cfg = _email_secrets()
    to_addr = professor_email()
    if not to_addr:
        return "E-mail do professor não configurado."
    if not smtp_configured():
        return (
            "Envio automático não configurado. O professor precisa definir a seção "
            "[email] nos secrets do app."
        )

    msg = EmailMessage()
    msg["Subject"] = _build_subject(student_name)
    msg["From"] = (cfg.get("from") or cfg["username"]).strip()
    msg["To"] = to_addr
    if student_email:
        msg["Reply-To"] = student_email
    msg.set_content(_build_body(student_name, student_email, extra_note))
    msg.add_attachment(
        file_bytes,
        maintype="application",
        subtype="json",
        filename=filename,
    )

    host = (cfg.get("smtp_host") or "smtp.gmail.com").strip()
    try:
        port = int(cfg.get("smtp_port", 587))
    except (TypeError, ValueError):
        port = 587

    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=20) as server:
                server.login(cfg["username"], cfg["password"])
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=20) as server:
                server.starttls()
                server.login(cfg["username"], cfg["password"])
                server.send_message(msg)
    except smtplib.SMTPAuthenticationError:
        return (
            "Falha de autenticação no servidor de e-mail. Para Gmail, use uma "
            "senha de app (myaccount.google.com/apppasswords)."
        )
    except Exception as exc:  # rede, DNS, timeout etc.
        return f"Não foi possível enviar o e-mail: {exc}"
    return None


def mailto_link(student_name: str, student_email: str | None) -> str:
    """Link mailto pré-preenchido (fallback quando o envio automático não está ativo)."""
    subject = quote(_build_subject(student_name))
    body = quote(
        _build_body(
            student_name,
            student_email,
            "(Anexei o arquivo de resultados baixado no app.)",
        )
    )
    return f"mailto:{professor_email()}?subject={subject}&body={body}"

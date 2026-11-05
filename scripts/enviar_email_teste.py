"""Envio REAL de um e-mail de teste pelo Resend usando enviar_email.

Uso, a partir da raiz do projeto:

    python scripts/enviar_email_teste.py --para seu-email@exemplo.com

Requer EMAIL_TOKEN no .env (ou no ambiente). Com o remetente
onboarding@resend.dev, o Resend só entrega ao e-mail dono da conta.
"""

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Meu_projeto.services.email_service import EmailEnvioError, enviar_email  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Envia um e-mail real de teste pelo Resend.")
    parser.add_argument("--para", required=True, help="Destinatário (o e-mail dono da conta Resend).")
    parser.add_argument("--assunto", default="Teste de envio NexStock")
    parser.add_argument("--mensagem", default="Se você recebeu este e-mail, o envio pelo NexStock funcionou.")
    parser.add_argument("--responder-para", default=None, help="Endereço de resposta (opcional).")
    args = parser.parse_args()

    horario = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    html = f"<h2>NexStock</h2><p>{args.mensagem}</p><p><small>Enviado em {horario}.</small></p>"

    print(f"Enviando para {args.para}...")
    try:
        message_id = asyncio.run(
            enviar_email(
                para=args.para,
                assunto=args.assunto,
                html=html,
                texto=f"{args.mensagem}\n\nEnviado em {horario}.",
                responder_para=args.responder_para,
            )
        )
    except EmailEnvioError as erro:
        print(f"FALHOU [{erro.codigo}]: {erro.message}")
        return 1

    print(f"ENVIADO. id da mensagem no Resend: {message_id}")
    print("Confira a caixa de entrada (e o spam) do destinatário.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# =============================================================================
# ChargeGrid AI Assistant — Sprint 03 (refactory LangChain LCEL)
# EV Challenge 2026 · FIAP + GoodWe
#
# Núcleo conversacional refeito em LangChain LCEL (Aula 01), memória por
# sessão com limite de tokens (Aula 02) e system prompt com XML tagging
# (Aula 04). Guardrails de escopo e anti-jailbreak em src/guardrails/.
#
# A saída estruturada Pydantic v2 (Aula 03, src/schemas/consulta_recarga.py
# + src/chain/builder.py::build_structured_chain) continua no projeto, mas
# não é mais exposta como comando no chat interativo — o comando "/consulta"
# foi removido por não se mostrar confiável na prática (ver conversa/README).
#
# Modelo: Ollama Cloud (gpt-oss:120b, configurável em .env) — nenhum modelo
# local, nenhuma API paga.
#
# A conversa é contínua: só termina quando o operador digitar um comando de
# saída (sair / exit / quit / tchau) ou usar Ctrl+C.
# =============================================================================

from __future__ import annotations

import uuid
from pathlib import Path

from dotenv import load_dotenv

from src.chain.builder import build_chat_with_memory
from src.chain.memoria import limpar_sessao
from src.guardrails.moderation import MENSAGEM_BLOQUEIO, eh_tentativa_de_jailbreak
from src.guardrails.scope_validator import (
    MENSAGEM_FORA_DE_ESCOPO,
    esta_fora_de_escopo,
    verificar_risco_profissional,
)

load_dotenv()

# Ancorado na localização deste arquivo (não no diretório de trabalho atual)
# — evita FileNotFoundError quando o script é rodado de outro lugar (ex.:
# botão "Run" da IDE em evals/run_evals.py, que usa evals/ como cwd).
BASE_DIR = Path(__file__).resolve().parent

COMANDOS_SAIDA = {"sair", "exit", "quit", "tchau"}

# -----------------------------------------------------------------------------
# DADOS OPERACIONAIS MOCKADOS (herdados da Sprint 02 — chatbot.py original)
# -----------------------------------------------------------------------------

DADOS_MOCK = {
    "sessoes_ativas": 3,
    "sessoes_hoje": 7,
    "kwh_hoje": 47.3,
    "demanda_kw": 28.5,
    "limite_kw": 35.0,
    "tarifa_pico": "R$ 2,80/kWh",
    "tarifa_fp": "R$ 1,50/kWh",
    "horario_pico": "18h às 21h",
    "faturamento": "R$ 132,70",
    "pico_horario": "18h30",
    "pico_kw": 33.2,
    "recomendacao": "Limite novas sessões a partir das 18h para evitar ultrapassagem do contrato.",
    "estacoes": {
        "Estação 1": {"status": "Operacional", "modelo": "GoodWe HCA G2 22kW", "kwh": 18.2},
        "Estação 2": {"status": "FALHA", "modelo": "GoodWe HCA G2 11kW", "kwh": 9.4},
        "Estação 3": {"status": "Operacional", "modelo": "GoodWe HCA G2 7kW", "kwh": 19.7},
    },
    "alertas": [
        "Estação 2: Alerta de Sobretensão detectado às 14h10 — novas sessões bloqueadas via OCPP"
    ],
}


def _formatar_dados_operacionais(mock: dict) -> str:
    estacoes = "\n".join(
        f"  - {nome}: {info['status']} | {info['modelo']} | {info['kwh']} kWh hoje"
        for nome, info in mock["estacoes"].items()
    )
    return (
        f"Sessões ativas: {mock['sessoes_ativas']}\n"
        f"Sessões concluídas hoje: {mock['sessoes_hoje']}\n"
        f"Consumo hoje: {mock['kwh_hoje']} kWh\n"
        f"Faturamento: {mock['faturamento']}\n"
        f"Demanda atual / limite: {mock['demanda_kw']} kW / {mock['limite_kw']} kW\n"
        f"Tarifa pico: {mock['tarifa_pico']} ({mock['horario_pico']})\n"
        f"Tarifa fora de pico: {mock['tarifa_fp']}\n"
        f"Previsão IA: pico de {mock['pico_kw']} kW às {mock['pico_horario']}\n"
        f"Recomendação IA: {mock['recomendacao']}\n"
        f"Estações:\n{estacoes}"
    )


def _formatar_alertas(mock: dict) -> str:
    if not mock["alertas"]:
        return "Nenhum alerta ativo."
    return "\n".join(f"- {alerta}" for alerta in mock["alertas"])


def carregar_system_prompt(mock: dict, caminho: str | Path | None = None) -> str:
    """Carrega o system prompt versionado (Aula 04) e injeta os dados
    operacionais dinâmicos nos placeholders {dados_operacionais}/{alertas}.

    `caminho` é resolvido a partir de BASE_DIR por padrão (não do diretório
    de trabalho atual), para funcionar igual rodando `python chatbot.py`,
    `python -m evals.run_evals` ou pelo botão Run da IDE em qualquer um
    dos arquivos que importam esta função.
    """
    if caminho is None:
        caminho = BASE_DIR / "prompts" / "system_prompt_v2.md"
    with open(caminho, encoding="utf-8") as f:
        template = f.read()
    return template.format(
        dados_operacionais=_formatar_dados_operacionais(mock),
        alertas=_formatar_alertas(mock),
    )


# -----------------------------------------------------------------------------
# GUARDRAILS + CHAIN
# -----------------------------------------------------------------------------


def processar_turno(pergunta: str, chain_com_memoria, session_id: str) -> str:
    """Aplica os guardrails (Bloco C) antes de decidir se chama o LLM."""
    if eh_tentativa_de_jailbreak(pergunta):
        return MENSAGEM_BLOQUEIO

    orientacao = verificar_risco_profissional(pergunta)
    if orientacao:
        return orientacao

    if esta_fora_de_escopo(pergunta):
        return MENSAGEM_FORA_DE_ESCOPO

    return chain_com_memoria.invoke(
        {"pergunta": pergunta},
        config={"configurable": {"session_id": session_id}},
    )


# -----------------------------------------------------------------------------
# CHAT INTERATIVO — loop contínuo, só termina quando o operador quiser
# -----------------------------------------------------------------------------


def iniciar_chat() -> None:
    system_prompt = carregar_system_prompt(DADOS_MOCK)
    chain_com_memoria = build_chat_with_memory(system_prompt)
    session_id = str(uuid.uuid4())

    print("=" * 65)
    print(" ChargeGrid AI Assistant — Sprint 03 (LangChain LCEL + Ollama Cloud)")
    print("=" * 65)
    print("Digite sua pergunta. Comandos especiais:")
    print("  sair | exit | quit | tchau  -> encerra a conversa")
    print("  /reset                      -> limpa a memória desta sessão\n")

    while True:
        try:
            entrada = input("Operador: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAté logo!")
            break

        if not entrada:
            continue

        if entrada.lower() in COMANDOS_SAIDA:
            print("Até logo!")
            break

        if entrada.lower() == "/reset":
            limpar_sessao(session_id)
            print("Memória da sessão limpa.\n")
            continue

        try:
            resposta = processar_turno(entrada, chain_com_memoria, session_id)
        except Exception as e:
            print(f"\nErro ao consultar o modelo: {e}\n")
            continue

        print(f"\nChargeGrid AI: {resposta}\n")


if __name__ == "__main__":
    iniciar_chat()
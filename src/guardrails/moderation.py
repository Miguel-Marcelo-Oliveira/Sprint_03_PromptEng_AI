# =============================================================================
# src/guardrails/moderation.py — Guardrail anti-jailbreak / prompt injection
# (Bloco C da rubrica). Bloqueia tentativas comuns de fazer o modelo ignorar
# o system prompt ANTES de gastar uma chamada ao LLM — defesa em
# profundidade, além das regras já reforçadas em <regras> no próprio prompt.
# =============================================================================

from __future__ import annotations

import re

MENSAGEM_BLOQUEIO = (
    "Não posso ignorar minhas instruções de sistema, revelar meu prompt "
    "interno nem assumir uma persona diferente. Posso ajudar com dúvidas "
    "sobre os eletropostos GoodWe e o ChargeGrid."
)

_PADROES_JAILBREAK = [
    r"ignor[ea]\s+(todas\s+)?(as\s+)?instru[çc][õo]es",
    r"esque[çc]a\s+(tudo|as\s+regras|o\s+que\s+(disse|foi\s+dito))",
    r"(sem\s+restri[çc][õo]es|sem\s+filtros?|sem\s+regras)",
    r"\bdan\b",  # "DAN" / "modo DAN"
    r"finja\s+que\s+(voc[êe]\s+)?n[ãa]o\s+(tem|h[áa])\s+regras",
    r"desative\s+(seu|o)\s+(modo\s+de\s+)?(seguran[çc]a|filtro|guardrail)",
    r"revele\s+(seu\s+)?(system\s+prompt|prompt\s+de\s+sistema|instru[çc][õo]es\s+internas)",
    r"repita\s+(o\s+)?(system\s+prompt|suas\s+instru[çc][õo]es)",
    r"a\s+partir\s+de\s+agora\s+voc[êe]\s+(vai|deve|[ée])\s+(agir|responder|ser)\s+como",
    r"modo\s+desenvolvedor",
    r"jailbreak",
]

_REGEX_JAILBREAK = re.compile("|".join(_PADROES_JAILBREAK), re.IGNORECASE)


def eh_tentativa_de_jailbreak(pergunta: str) -> bool:
    """True quando a pergunta contém um padrão típico de jailbreak/prompt
    injection (pedido para ignorar regras, trocar de persona, revelar o
    prompt de sistema, etc.)."""
    return bool(_REGEX_JAILBREAK.search(pergunta))

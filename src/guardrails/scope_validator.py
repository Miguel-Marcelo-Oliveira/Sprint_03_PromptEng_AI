# =============================================================================
# src/guardrails/scope_validator.py — Guardrail de escopo (Bloco C da
# rubrica): mantém o assistente restrito ao domínio GoodWe/ChargeGrid e
# redireciona pedidos de aconselhamento jurídico, financeiro ou de segurança
# elétrica para um profissional habilitado, em vez de responder diretamente.
# =============================================================================

from __future__ import annotations

import re
from typing import Optional

MENSAGEM_FORA_DE_ESCOPO = (
    "Posso ajudar com informações sobre os eletropostos e sessões GoodWe."
)

MENSAGEM_ORIENTAR_PROFISSIONAL = (
    "Não posso dar aconselhamento {area}. Recomendo consultar {sugestao} "
    "antes de tomar qualquer decisão."
)

# Padrões claramente fora do domínio GoodWe/ChargeGrid — bloqueio automático,
# sem gastar uma chamada ao LLM.
_PADROES_FORA_DE_ESCOPO = [
    re.compile(r"melhor\s+carro", re.IGNORECASE),
    re.compile(r"qual\s+carro.*(comprar|escolher)", re.IGNORECASE),
    re.compile(r"previs[ãa]o\s+do\s+tempo", re.IGNORECASE),
    re.compile(r"resultado\s+d[oe]\s+jogo", re.IGNORECASE),
    re.compile(r"receita\s+de\s+\w+", re.IGNORECASE),
    re.compile(r"capital\s+d[oe]\s+\w+", re.IGNORECASE),
    re.compile(r"\b(poema|piada|hor[óo]scopo)\b", re.IGNORECASE),
    re.compile(r"c[óo]digo\s+em\s+(python|javascript|java)\s+para", re.IGNORECASE),
    re.compile(r"quem\s+(foi|é)\s+", re.IGNORECASE),
]

# Pedidos que exigem orientação a um profissional em vez de conselho direto.
# Cada item: (padrão, área citada na mensagem, profissional sugerido)
_PADROES_RISCO_PROFISSIONAL = [
    (
        re.compile(r"\b(process\w*|entrar\s+com\s+(uma\s+)?a[çc][ãa]o|a[çc][ãa]o\s+judicial|contrato|responsabilidade\s+civil|direito)\b", re.IGNORECASE),
        "jurídico",
        "um advogado",
    ),
    (
        re.compile(r"\b(investir|a[çc][õo]es|financiamento|empr[ée]stimo|declarar\s+(o\s+)?imposto)\b", re.IGNORECASE),
        "financeiro",
        "um consultor financeiro",
    ),
    (
        re.compile(r"\b(fia[çc][ãa]o|disjuntor|aterramento|choque\s+el[ée]trico|mexer\s+n[ao]\s+instala[çc][ãa]o)\b", re.IGNORECASE),
        "de segurança elétrica",
        "um eletricista credenciado",
    ),
]


def esta_fora_de_escopo(pergunta: str) -> bool:
    """True quando a pergunta claramente não é sobre GoodWe/ChargeGrid."""
    return any(padrao.search(pergunta) for padrao in _PADROES_FORA_DE_ESCOPO)


def verificar_risco_profissional(pergunta: str) -> Optional[str]:
    """Retorna a mensagem de orientação se a pergunta pedir aconselhamento
    jurídico, financeiro ou de segurança elétrica sensível; None caso
    contrário (segue para o fluxo normal)."""
    for padrao, area, sugestao in _PADROES_RISCO_PROFISSIONAL:
        if padrao.search(pergunta):
            return MENSAGEM_ORIENTAR_PROFISSIONAL.format(area=area, sugestao=sugestao)
    return None

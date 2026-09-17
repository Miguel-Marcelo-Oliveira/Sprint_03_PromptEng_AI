# =============================================================================
# prompts/medir_tokens.py — mede em tokens o ganho do context engineering
# (Aula 04) entre system_prompt_v1.md (bloco único) e system_prompt_v2.md
# (XML tagging).
#
# Rodar:  python prompts/medir_tokens.py
# Requer: pip install tiktoken  (já em requirements.txt)
#
# CORREÇÃO (pós-revisão): além de imprimir no console, o resultado agora é
# gravado em prompts/tokens_resultado.json — isso permite que
# docs/gerar_relatorio_evolucao.py preencha a coluna "Tokens por turno" da
# tabela antes/depois automaticamente, sem precisar colar o número à mão.
# =============================================================================

from __future__ import annotations

import json
from pathlib import Path

import tiktoken

PASTA = Path(__file__).parent


def contar_tokens(texto: str, modelo: str = "gpt-4") -> int:
    """Conta tokens usando o tokenizador do modelo especificado.
    Tiktoken serve como aproximação de BPE
    consistente para comparar as duas
    versões do prompt entre si."""
    enc = tiktoken.encoding_for_model(modelo)
    return len(enc.encode(texto))


def carregar_sem_placeholders(caminho: Path) -> str:
    """Remove os placeholders {dados_operacionais}/{alertas} antes de medir,
    já que eles têm tamanho variável e não fazem parte do texto fixo do
    prompt (o que estamos comparando é a instrução em si)."""
    texto = caminho.read_text(encoding="utf-8")
    return (
        texto.replace("{dados_operacionais}", "")
        .replace("{alertas}", "")
    )


def main() -> None:
    v1 = carregar_sem_placeholders(PASTA / "system_prompt_v1.md")
    v2 = carregar_sem_placeholders(PASTA / "system_prompt_v2.md")

    tok_v1 = contar_tokens(v1)
    tok_v2 = contar_tokens(v2)
    reducao = (1 - tok_v2 / tok_v1) * 100 if tok_v1 else 0.0

    print(f"system_prompt_v1.md: {tok_v1} tokens")
    print(f"system_prompt_v2.md: {tok_v2} tokens")
    print(f"Redução: {reducao:.1f}%")

    resultado = {
        "tokens_v1": tok_v1,
        "tokens_v2": tok_v2,
        "reducao_pct": round(reducao, 1),
    }
    saida = PASTA / "tokens_resultado.json"
    saida.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    print()
    print(f"Resultado gravado em {saida}")
    print(
        "Cole esse resultado em prompts/versoes.md — e rode "
        "docs/gerar_relatorio_evolucao.py para atualizar o PDF automaticamente."
    )


if __name__ == "__main__":
    main()

# =============================================================================
# evals/comparar_modelos.py — roda o mesmo conjunto de perguntas em 2+
# modelos do Ollama Cloud com os MESMOS parâmetros, para alimentar
# docs/relatorio_modelos.md (item obrigatório 6.2: comparar 2+ modelos e
# documentar temperature, top_p e max_tokens).
#
# NÃO é chamada multi-provider (isso é o bônus, fora do escopo pedido) —
# aqui é o MESMO provedor (Ollama Cloud), comparando modelos diferentes.
#
# Rodar a partir da raiz do projeto:
#   python -m evals.comparar_modelos
# =============================================================================

from __future__ import annotations

import json
import time
from pathlib import Path

from chatbot import DADOS_MOCK, carregar_system_prompt
from src.chain.builder import build_chat_chain, build_llm

# Modelos comparados — troque livremente pelos disponíveis na sua conta
# Ollama Cloud (ex.: `ollama list` ou https://ollama.com/search?c=cloud).
MODELOS = ["gpt-oss:120b", "nemotron-3-nano:30b"]

# Mesmos parâmetros para os dois modelos — isola a variável "modelo" na
# comparação (mesmo racional do teste A/B da Aula 04).
#
# top_p agora é obrigatório e fixo em 0.95 (mesmo default de
# src/chain/builder.py::build_llm) — omitir o top_p deixa a critério do padrão
# embutido em cada modelo no Ollama Cloud, que varia de um modelo para outro.
PARAMETROS = {"temperature": 0.3, "num_predict": 512, "top_p": 0.95}

PERGUNTAS_TESTE = [
    "Quantas sessões estão ativas agora e qual o consumo total hoje?",
    "A demanda atual está próxima do limite? Devo me preocupar?",
    "Tem algum problema nas estações agora?",
]


def rodar(mostrar_no_console: bool = True) -> dict:
    system_prompt = carregar_system_prompt(DADOS_MOCK)
    resultado: dict = {"parametros": PARAMETROS, "modelos": {}}

    for nome_modelo in MODELOS:
        if mostrar_no_console:
            print("=" * 70)
            print(f"Modelo: {nome_modelo}")
            print("=" * 70)

        llm = build_llm(model=nome_modelo, **PARAMETROS)
        chain = build_chat_chain(system_prompt, llm)
        respostas = []
        for i, pergunta in enumerate(PERGUNTAS_TESTE, start=1):
            inicio = time.time()
            resposta = chain.invoke({"pergunta": pergunta, "history": []})
            latencia = time.time() - inicio
            respostas.append(
                {"pergunta": pergunta, "resposta": resposta, "latencia_s": round(latencia, 2)}
            )

            if mostrar_no_console:
                print(f"\n[{i}] {pergunta}")
                print("-" * 70)
                print(resposta)
                print(f"\n(latência: {latencia:.2f}s)")

        resultado["modelos"][nome_modelo] = respostas
        if mostrar_no_console:
            print()

    return resultado


if __name__ == "__main__":
    dados = rodar()
    saida = Path(__file__).parent / "resultados_comparacao_modelos.json"
    saida.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Resultados gravados em {saida}")
    print("Use esses dados para preencher a tabela de docs/relatorio_modelos.md")
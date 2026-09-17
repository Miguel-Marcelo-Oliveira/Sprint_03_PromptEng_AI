# =============================================================================
# evals/run_evals.py — roda evals/eval_set.py contra a chain refatorada da
# Sprint 03 e grava o resultado em evals/sprint3_results.json.
#
# Requer OLLAMA_API_KEY configurada em .env — cada execução faz chamadas
# reais ao Ollama Cloud (gratuitas, mas ainda assim chamadas de rede).
#
# Rodar a partir da raiz do projeto:
#   python -m evals.run_evals
#
# CORREÇÃO (pós-revisão): este script rodava só happy path, memória e
# guardrails — CASOS_STRUCTURED_OUTPUT e CASOS_VALIDACAO_SCHEMA_INVALIDA
# (definidos em evals/eval_set.py) nunca eram executados, então a saída
# estruturada Pydantic v2 (item 3 do escopo / Bloco A da rubrica) ficava sem
# nenhuma prova real de que funciona — e a coluna "Acurácia do structured
# output" da tabela antes/depois (§8.3 do PDF) não tinha como ser preenchida
# honestamente. Agora o resultado sai em resultados["structured_output"].
# =============================================================================

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

from pydantic import ValidationError
from langchain_core.exceptions import OutputParserException

from chatbot import DADOS_MOCK, carregar_system_prompt, processar_turno
from src.chain.builder import build_chat_with_memory, build_structured_chain
from src.chain.memoria import limpar_sessao
from src.schemas.consulta_recarga import ConsultaRecarga
from evals.eval_set import (
    CASOS_FORA_DE_ESCOPO,
    CASOS_HAPPY_PATH,
    CASOS_JAILBREAK,
    CASOS_MEMORIA,
    CASOS_RISCO_PROFISSIONAL,
    CASOS_STRUCTURED_OUTPUT,
    CASOS_VALIDACAO_SCHEMA_INVALIDA,
)


def _bate_esperado(resposta: str, termos: list[str]) -> bool:
    resposta_low = resposta.lower()
    return all(termo.lower() in resposta_low for termo in termos)


def _confere_campos_estruturados(
    resultado: ConsultaRecarga, esperado: dict
) -> tuple[bool, list[str]]:
    """Compara os campos do objeto `ConsultaRecarga` retornado pela chain com
    os valores esperados do caso de teste. Retorna (passou, motivos_de_falha)
    — a lista de motivos vai para o JSON para facilitar depuração manual."""
    falhas: list[str] = []

    def _confere(nome: str, obtido, esperado_valor, tolerancia: float = 0.0) -> None:
        diferente = (
            abs(obtido - esperado_valor) > tolerancia if tolerancia else obtido != esperado_valor
        )
        if diferente:
            falhas.append(f"{nome}: esperado {esperado_valor!r}, obtido {obtido!r}")

    if "sessoes_ativas" in esperado:
        _confere("sessoes_ativas", resultado.sessoes_ativas, esperado["sessoes_ativas"])
    if "kwh_hoje" in esperado:
        _confere("kwh_hoje", resultado.kwh_hoje, esperado["kwh_hoje"], tolerancia=0.01)
    if "limite_kw" in esperado:
        _confere("limite_kw", resultado.limite_kw, esperado["limite_kw"], tolerancia=0.01)
    if "demanda_kw" in esperado:
        _confere("demanda_kw", resultado.demanda_kw, esperado["demanda_kw"], tolerancia=0.01)
    if "tarifa_atual" in esperado:
        _confere("tarifa_atual", resultado.tarifa_atual, esperado["tarifa_atual"])
    if "num_estacoes" in esperado:
        _confere("num_estacoes", len(resultado.estacoes), esperado["num_estacoes"])
    if "alerta_contem" in esperado:
        termo = esperado["alerta_contem"].lower()
        alerta = (resultado.alerta or "").lower()
        if termo not in alerta:
            falhas.append(
                f"alerta: esperado conter {esperado['alerta_contem']!r}, obtido {resultado.alerta!r}"
            )
    if esperado.get("alerta_none") and resultado.alerta not in (None, ""):
        falhas.append(f"alerta: esperado None/vazio, obtido {resultado.alerta!r}")

    return (len(falhas) == 0, falhas)


def _rodar_structured_output() -> list[dict]:
    """Executa `build_structured_chain()` para cada caso de
    CASOS_STRUCTURED_OUTPUT e confere os campos do objeto `ConsultaRecarga`
    retornado (item 3 do escopo / Bloco A da rubrica).

    CORREÇÃO (pós-revisão): antes só se previa `ValidationError` (JSON
    válido, mas campo/tipo errado). Na prática o modelo às vezes devolve
    JSON incompleto (truncado por num_predict) — isso levanta
    `OutputParserException` ANTES de o Pydantic sequer validar o schema, e
    sem tratar essa exceção o script inteiro morria no meio, perdendo
    inclusive os resultados de happy path/memória/guardrails já rodados.
    Agora qualquer uma das duas falhas é registrada como caso reprovado
    (com o motivo) em vez de derrubar o eval — com uma segunda tentativa
    antes de desistir, já que o modelo não é 100% determinístico."""
    chain = build_structured_chain()
    saida = []
    for caso in CASOS_STRUCTURED_OUTPUT:
        ultimo_erro: Exception | None = None
        for tentativa in range(2):  # 1 nova tentativa antes de marcar como falha
            try:
                resultado = chain.invoke(
                    {"contexto": caso["contexto"], "pergunta": caso["pergunta"]}
                )
                passou, motivos = _confere_campos_estruturados(
                    resultado, caso["campos_esperados"]
                )
                saida.append(
                    {
                        "id": caso["id"],
                        "categoria": caso["categoria"],
                        "passou": passou,
                        "motivos_falha": motivos,
                        "tentativas": tentativa + 1,
                        "objeto_retornado": resultado.model_dump(),
                    }
                )
                break
            except (ValidationError, OutputParserException) as e:
                ultimo_erro = e
                continue
            except Exception as e:  # pragma: no cover - defensivo
                ultimo_erro = e
                continue
        else:
            saida.append(
                {
                    "id": caso["id"],
                    "categoria": caso["categoria"],
                    "passou": False,
                    "tentativas": 2,
                    "motivos_falha": [
                        f"{type(ultimo_erro).__name__} nas 2 tentativas: {ultimo_erro}"
                    ],
                }
            )
    return saida


def _rodar_validacao_schema_invalida() -> list[dict]:
    """Instancia `ConsultaRecarga` diretamente com dados inválidos (mesmo
    padrão do gabarito da Aula 03) e confere que o field_validator
    'demanda_dentro_do_plausivel' rejeita — teste determinístico, sem
    depender do LLM."""
    saida = []
    for caso in CASOS_VALIDACAO_SCHEMA_INVALIDA:
        try:
            ConsultaRecarga(**caso["kwargs_invalidos"])
        except ValidationError as e:
            saida.append(
                {
                    "id": caso["id"],
                    "categoria": caso["categoria"],
                    "passou": True,
                    "motivo": f"ValidationError levantado como esperado: {e.errors()[0]['msg']}",
                }
            )
        except Exception as e:  # pragma: no cover - defensivo
            saida.append(
                {
                    "id": caso["id"],
                    "categoria": caso["categoria"],
                    "passou": False,
                    "motivo": f"Erro inesperado ({type(e).__name__}): {e}",
                }
            )
        else:
            saida.append(
                {
                    "id": caso["id"],
                    "categoria": caso["categoria"],
                    "passou": False,
                    "motivo": "Nenhum ValidationError levantado — o schema aceitou dados inválidos.",
                }
            )
    return saida


def rodar() -> dict:
    system_prompt = carregar_system_prompt(DADOS_MOCK)
    chain = build_chat_with_memory(system_prompt)

    resultados: dict = {
        "happy_path": [],
        "memoria": [],
        "fora_de_escopo": [],
        "risco_profissional": [],
        "jailbreak": [],
        "structured_output": {},
    }

    # --- happy path (comparável ao resultados_testes.md da Sprint 02) ----
    for caso in CASOS_HAPPY_PATH:
        session_id = str(uuid.uuid4())
        inicio = time.time()
        resposta = processar_turno(caso["pergunta"], chain, session_id)
        latencia = time.time() - inicio
        resultados["happy_path"].append(
            {
                **caso,
                "resposta": resposta,
                "latencia_s": round(latencia, 2),
                "passou": _bate_esperado(resposta, caso["esperado_contem"]),
            }
        )

    # --- memória: mesma sessão, vários turnos -----------------------------
    session_memoria = str(uuid.uuid4())
    limpar_sessao(session_memoria)
    for caso in CASOS_MEMORIA:
        inicio = time.time()
        resposta = processar_turno(caso["pergunta"], chain, session_memoria)
        latencia = time.time() - inicio
        resultados["memoria"].append(
            {**caso, "resposta": resposta, "latencia_s": round(latencia, 2)}
        )

    # --- guardrails: fora de escopo / risco profissional / jailbreak -----
    for chave, casos in [
        ("fora_de_escopo", CASOS_FORA_DE_ESCOPO),
        ("risco_profissional", CASOS_RISCO_PROFISSIONAL),
        ("jailbreak", CASOS_JAILBREAK),
    ]:
        for caso in casos:
            session_id = str(uuid.uuid4())
            resposta = processar_turno(caso["pergunta"], chain, session_id)
            resultados[chave].append({**caso, "resposta": resposta})

    # --- saída estruturada (Aula 03 / item 3 do escopo) --------------------
    casos_extracao = _rodar_structured_output()
    casos_validacao = _rodar_validacao_schema_invalida()
    total = len(casos_extracao) + len(casos_validacao)
    acertos = sum(1 for c in casos_extracao if c["passou"]) + sum(
        1 for c in casos_validacao if c["passou"]
    )
    resultados["structured_output"] = {
        "extracao": casos_extracao,
        "validacao_schema": casos_validacao,
        "acertos": acertos,
        "total": total,
        "acuracia_pct": round(100 * acertos / total, 1) if total else 0.0,
    }

    return resultados


if __name__ == "__main__":
    dados = rodar()
    saida = Path(__file__).parent / "sprint3_results.json"
    saida.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Resultados gravados em {saida}")

    so = dados["structured_output"]
    print(
        f"Structured output (ConsultaRecarga): {so['acertos']}/{so['total']} "
        f"casos corretos ({so['acuracia_pct']}%)"
    )
    print("Rode 'python docs/gerar_relatorio_evolucao.py' para atualizar o PDF com esses números.")

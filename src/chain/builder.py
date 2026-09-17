# =============================================================================
# src/chain/builder.py — Núcleo conversacional em LangChain LCEL (Aula 01),
# memória por sessão (Aula 02) e saída estruturada Pydantic v2 (Aula 03).
# =============================================================================
#
# Todos os modelos de IA usados aqui rodam no Ollama Cloud (base_url
# https://ollama.com) — nenhum modelo local, nenhuma API paga. Exige
# OLLAMA_API_KEY configurada (ver .env.example).

from __future__ import annotations

import os
from typing import Optional

from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_ollama import ChatOllama

from src.chain.memoria import get_session_history
from src.schemas.consulta_recarga import ConsultaRecarga

MODELO_PADRAO = os.getenv("OLLAMA_MODEL", "gpt-oss:120b")


def configurar_ollama_cloud() -> None:
    """Garante que o cliente aponte para o Ollama Cloud — nunca uma
    instância local — e que a API key exista antes de qualquer chamada."""
    os.environ.setdefault("OLLAMA_HOST", "https://ollama.com")
    if not os.getenv("OLLAMA_API_KEY"):
        raise EnvironmentError(
            "OLLAMA_API_KEY não encontrada.\n"
            "Copie .env.example para .env e cole uma API key gratuita "
            "gerada em https://ollama.com."
        )


def build_llm(
    model: str = MODELO_PADRAO,
    temperature: float = 0.3,
    num_predict: int = 512,
    top_p: float = 0.95,
    formato_json: bool = False,
) -> ChatOllama:
    """Instancia o ChatOllama apontando para o Ollama Cloud.

    Parâmetros documentados em docs/relatorio_modelos.md: temperature
    (aleatoriedade), num_predict (equivalente a max_tokens), top_p
    (nucleus sampling) e format="json" quando a saída precisa ser JSON
    (usado pela chain estruturada).

    `top_p` agora é obrigatório em todas as chamadas — não fica mais a
    critério do padrão embutido em cada modelo no Ollama Cloud (que nem é sempre o mesmo valor).
    O padrão do projeto é `0.95`;
    passe um valor diferente explicitamente (ex.: `build_llm(top_p=0.8)`)
    se quiser testar outro cenário.
    """
    configurar_ollama_cloud()
    return ChatOllama(
        model=model,
        temperature=temperature,
        num_predict=num_predict,
        top_p=top_p,
        **({"format": "json"} if formato_json else {}),
    )


def build_chat_chain(system_prompt: str, llm: Optional[ChatOllama] = None):
    """Chain LCEL conversacional: prompt (com placeholder de histórico) |
    llm | StrOutputParser — reconstrói o núcleo manual das Sprints 1/2."""
    llm = llm or build_llm()
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            MessagesPlaceholder("history"),
            ("human", "{pergunta}"),
        ]
    )
    return prompt | llm | StrOutputParser()


def build_chat_with_memory(
    system_prompt: str,
    llm: Optional[ChatOllama] = None,
    max_token_limit: int = 800,
):
    """Envolve a chain conversacional com memória por sessão e limite de
    tokens (src/chain/memoria.py) via RunnableWithMessageHistory."""
    chain = build_chat_chain(system_prompt, llm)
    return RunnableWithMessageHistory(
        chain,
        lambda session_id: get_session_history(session_id, max_token_limit),
        input_messages_key="pergunta",
        history_messages_key="history",
    )


def build_structured_chain(llm: Optional[ChatOllama] = None):
    """Chain de saída estruturada: devolve um objeto `ConsultaRecarga`
    validado, não texto livre (Aula 03). Combina format="json" do Ollama
    (garante JSON sintaticamente válido) com PydanticOutputParser (garante
    os campos, os tipos e as regras do schema).

    CORREÇÃO (pós-revisão): esta chain usava o num_predict padrão (512),
    pensado para respostas de chat em texto livre. Modelos "reasoning" como
    o gpt-oss:120b gastam parte desse orçamento pensando internamente antes
    de escrever a resposta — somado ao JSON de ConsultaRecarga (que inclui
    uma lista de estações aninhadas), 512 tokens não bastam e a saída sai
    cortada no meio do JSON, o que o PydanticOutputParser reporta como
    `OutputParserException: Invalid json output` (ver evals/run_evals.py).
    Aumentamos a folga aqui e reforçamos no prompt para não gastar tokens
    com raciocínio visível.
    """
    parser = PydanticOutputParser(pydantic_object=ConsultaRecarga)
    llm = llm or build_llm(formato_json=True, num_predict=1024)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Você é um extrator de dados operacionais do ChargeGrid (GoodWe). "
                "Extraia SOMENTE os dados presentes no contexto abaixo — nunca "
                "invente valores. Responda SOMENTE com o objeto JSON final — "
                "sem nenhum texto de raciocínio, explicação ou markdown antes "
                "ou depois dele.\n{format_instructions}",
            ),
            ("human", "Contexto operacional:\n{contexto}\n\nPergunta: {pergunta}"),
        ]
    ).partial(format_instructions=parser.get_format_instructions())
    return prompt | llm | parser
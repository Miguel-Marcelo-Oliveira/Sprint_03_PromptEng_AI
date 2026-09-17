# =============================================================================
# src/chain/memoria.py — Memória conversacional por sessão com limite de
# tokens (Aula 02).
# =============================================================================

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

import tiktoken
from langchain_core.chat_history import BaseChatMessageHistory, InMemoryChatMessageHistory
from langchain_core.messages import BaseMessage

# cl100k_base é uma aproximação de BPE válida para medir/limitar tokens de
# qualquer modelo — o mesmo raciocínio usado com tiktoken na Aula 04.
_ENCODER = tiktoken.get_encoding("cl100k_base")


def _contar_tokens(mensagens: Sequence[BaseMessage]) -> int:
    total = 0
    for m in mensagens:
        conteudo = m.content if isinstance(m.content, str) else str(m.content)
        total += len(_ENCODER.encode(conteudo))
    return total


class TokenBufferChatMessageHistory(InMemoryChatMessageHistory):
    """Histórico em memória com janela deslizante por limite de tokens.

    Mesma ideia da ConversationTokenBufferMemory da Aula 02: ao ultrapassar
    `max_token_limit`, descarta as mensagens mais antigas primeiro — mas
    implementado como BaseChatMessageHistory para funcionar com
    RunnableWithMessageHistory.
    """

    max_token_limit: int = 800

    def add_messages(self, messages: Sequence[BaseMessage]) -> None:
        super().add_messages(messages)
        self._aplicar_limite()

    def _aplicar_limite(self) -> None:
        # mantém sempre pelo menos o último par (pergunta/resposta) mesmo
        # que ele sozinho ultrapasse o limite — evita ficar sem contexto.
        while len(self.messages) > 2 and _contar_tokens(self.messages) > self.max_token_limit:
            self.messages.pop(0)


# Armazenamento em memória: um histórico por session_id (multiusuário),
# mesmo padrão de `store = {}` + `get_session_history()` da nota técnica
# "memória em LCEL moderno" da Aula 02.
_store: Dict[str, TokenBufferChatMessageHistory] = {}


def get_session_history(session_id: str, max_token_limit: int = 800) -> BaseChatMessageHistory:
    """Retorna (criando se necessário) o histórico da sessão `session_id`."""
    if session_id not in _store:
        _store[session_id] = TokenBufferChatMessageHistory(max_token_limit=max_token_limit)
    return _store[session_id]


def limpar_sessao(session_id: str) -> None:
    """Remove o histórico de uma sessão (ex.: comando /reset no chat)."""
    _store.pop(session_id, None)


def tokens_na_sessao(session_id: str) -> int:
    """Quantos tokens estão hoje no histórico da sessão — útil para depurar
    e para o relatório de evolução (coluna 'tokens por turno')."""
    if session_id not in _store:
        return 0
    return _contar_tokens(_store[session_id].messages)


def mensagens_na_sessao(session_id: str) -> Optional[List[BaseMessage]]:
    """Acesso somente-leitura às mensagens guardadas (para testes/inspeção)."""
    if session_id not in _store:
        return None
    return list(_store[session_id].messages)

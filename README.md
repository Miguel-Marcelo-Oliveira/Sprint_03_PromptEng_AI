# ChargeGrid AI Assistant

EV Challenge 2026 · FIAP + GoodWe — **Sprint 03** (refactory LangChain LCEL)


---

## O que mudou na Sprint 03

O núcleo conversacional foi reconstruído em **LangChain LCEL**, seguindo o
Módulo 1 do curso (Aulas 01–04), e passou a rodar 100% no **Ollama Cloud**
(`gpt-oss:120b`) — **sem API paga**.

| Antes (Sprints 1/2) | Agora (Sprint 03) |
|---|---|
| Chamadas manuais à API da Groq | Chain LCEL: `ChatPromptTemplate \| ChatOllama \| parser` |
| Histórico em lista Python, sem limite | Memória por sessão com limite de tokens (`RunnableWithMessageHistory`) |
| Sempre texto livre | Saída estruturada opcional e validada (Pydantic v2) |
| `system_prompt` em f-string única | Versionado, com XML tagging (`prompts/`) |
| Guardrails só no texto do prompt | Guardrails também em código (`src/guardrails/`) |
| RAG com sentence-transformers local | Fora do escopo desta sprint (ver PDF do Challenge, seção 3) — `rag.py` preservado só como histórico, não é usado |

Detalhes de decisão técnica, trade-offs e os problemas encontrados estão em
[`docs/relatorio_evolucao.pdf`](./docs/relatorio_evolucao.pdf).

---

## Estrutura do repositório

```
chargegrid-assistant/
├── requirements.txt
├── .env.example
├── .gitignore                     # protege .env — nunca versionar a API key
├── prompts/
│   ├── system_prompt_v1.md        # baseline (Sprints 1/2), sem XML tagging
│   ├── system_prompt_v2.md        # usado pela chain — XML tagging (Aula 04)
│   ├── versoes.md                 # tabela de versões do prompt
│   ├── medir_tokens.py            # mede o ganho de tokens v1 → v2 (tiktoken)
│   └── tokens_resultado.json      # gerado por medir_tokens.py (lido pelo relatório)
├── src/
│   ├── chain/
│   │   ├── builder.py             # chain LCEL + memória + saída estruturada
│   │   └── memoria.py             # memória por sessão com limite de tokens
│   ├── schemas/
│   │   └── consulta_recarga.py    # schema Pydantic v2 do domínio EV
│   └── guardrails/
│       ├── scope_validator.py     # escopo GoodWe + risco jurídico/financeiro/elétrico
│       └── moderation.py          # anti-jailbreak / prompt injection
├── evals/
│   ├── eval_set.py                # happy path + memória + escopo + jailbreak + structured output
│   ├── run_evals.py                # roda o eval set inteiro -> sprint3_results.json
│   ├── comparar_modelos.py         # compara 2+ modelos com os mesmos parâmetros
│   ├── sprint3_results.json        # resultado real da última rodada (regravar antes de entregar)
│   └── resultados_comparacao_modelos.json
└── docs/
    ├── relatorio_modelos.md        # parâmetros e comparação de modelos
    └── relatorio_evolucao.pdf      # relatório de evolução 
    
```

---

## Como rodar

### 1. Pré-requisitos

- Python 3.10+
- Conta gratuita em [ollama.com](https://ollama.com) (o plano **Free** já
  inclui acesso a modelos na nuvem — sem cartão de crédito)

### 2. Instalar dependências

```bash
pip install -r requirements.txt
```

### 3. Configurar variáveis de ambiente

```bash
cp .env.example .env
```

Edite `.env`:

```
OLLAMA_HOST=https://ollama.com
OLLAMA_API_KEY=sua_chave_gerada_em_ollama.com/settings/keys
OLLAMA_MODEL=gpt-oss:120b
```

**Nunca** faça commit do `.env` (já está no `.gitignore`).

### 4. Rodar o chat

```bash
python chatbot.py
```

A conversa é **contínua** — só termina quando o operador digitar `sair`,
`exit`, `quit` ou `tchau` (ou `Ctrl+C`). Comando especial:

- `/reset` — limpa a memória da sessão atual

### 5. Reexecutar o eval e a comparação de modelos (antes da entrega final)

```bash
python -m evals.run_evals          # gera evals/sprint3_results.json (inclui structured output)
python -m evals.comparar_modelos   # gera evals/resultados_comparacao_modelos.json
python prompts/medir_tokens.py     # mede o ganho de tokens do prompt v1 -> v2 -> tokens_resultado.json
```

---

## Guardrails (Bloco C da rubrica)

Antes de qualquer chamada ao modelo, `chatbot.py::processar_turno` passa a
pergunta por três checagens de código (`src/guardrails/`):

1. **Anti-jailbreak** (`moderation.eh_tentativa_de_jailbreak`) — bloqueia
   pedidos para ignorar instruções, revelar o system prompt ou assumir
   outra persona.
2. **Risco profissional** (`scope_validator.verificar_risco_profissional`) —
   pedidos de aconselhamento jurídico, financeiro ou de segurança elétrica
   são recusados com orientação para procurar um profissional habilitado.
3. **Escopo GoodWe** (`scope_validator.esta_fora_de_escopo`) — bloqueia
   perguntas claramente fora do domínio (ex.: "qual o melhor carro elétrico
   para comprar"). Perguntas ambíguas seguem para o LLM, que tem a mesma
   regra reforçada no `<escopo>` do system prompt v2 — defesa em duas
   camadas.

Esses três comportamentos são exercitados em `evals/eval_set.py`
(`CASOS_FORA_DE_ESCOPO`, `CASOS_RISCO_PROFISSIONAL`, `CASOS_JAILBREAK`).

---

## Saída estruturada (Bloco A da rubrica)

`src/schemas/consulta_recarga.py` define `ConsultaRecarga` (Pydantic v2, com
`field_validator` cruzando `demanda_kw`/`limite_kw`) e
`src/chain/builder.py::build_structured_chain()` monta a chain
`prompt | ChatOllama(format="json") | PydanticOutputParser`. Isso não é mais
exposto como comando no chat interativo (removemos o `/consulta` por não se
mostrar confiável na prática), mas continua sendo validado automaticamente em
`evals/run_evals.py` — `CASOS_STRUCTURED_OUTPUT` confere os campos extraídos
e `CASOS_VALIDACAO_SCHEMA_INVALIDA` confirma que dados inválidos são
rejeitados pelo schema. O resultado (`structured_output.acuracia_pct`) vai
para `evals/sprint3_results.json` e alimenta a tabela antes/depois do
relatório de evolução.

---

## Integrantes

| Nome                                        | RM     |
|---------------------------------------------|--------|
| Miguel Marcelo Alves Ramos de Oliveira      | 569467 |
| Felipe de Oliveira Doern                    | 568798 |
| Tom Stringasci Albuquerque Coelho de Morais | 568844 |
| Eric dos Santos Mendes da Silva             | 569528 |
| Ligia de Andrade Matheus                    | 568973 |

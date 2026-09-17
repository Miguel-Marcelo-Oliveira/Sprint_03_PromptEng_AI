# Relatório de uso de modelos e parâmetros — Sprint 03

**ChargeGrid AI Assistant · EV Challenge 2026 · FIAP + GoodWe**

Todos os modelos rodam no **Ollama Cloud** (`OLLAMA_HOST=https://ollama.com`) —
sem custo, sem modelo local. Não há chamada multi-provider aqui: os dois
modelos comparados vêm do **mesmo provedor** (Ollama), apenas trocando o
parâmetro `model` do `ChatOllama` — a chamada multi-provider real é o item
de bônus (+1 pt) e foi deixada fora do escopo desta entrega.

## 1. Modelos comparados

| Modelo | Onde é usado |
|---|---|
| `gpt-oss:120b` | `src/chain/builder.py::MODELO_PADRAO`, chat principal e chain estruturada |
| `nemotron-3-nano:30b` | `evals/comparar_modelos.py` |

> Troque `nemotron-3-nano:30b` por qualquer outro modelo disponível na sua conta Ollama
>  (`ollama list` ou https://ollama.com/search?c=cloud) se preferir.

## 2. Parâmetros documentados

Os dois modelos foram testados com os **mesmos parâmetros** em
`evals/comparar_modelos.py`, para isolar a variável "modelo" na comparação:

| Parâmetro | Valor usado | Onde é definido | Observação |
|---|---|---|---|
| `temperature` | `0.3` | `src/chain/builder.py::build_llm` (padrão) | Baixa aleatoriedade — o assistente reporta números operacionais, não faz brainstorm. |
| `num_predict` (equivalente a `max_tokens`) | `512` no chat conversacional; `1024` na chain estruturada (`build_structured_chain`) | `src/chain/builder.py::build_llm` | 512 é suficiente para respostas de 1–3 parágrafos. A chain estruturada precisa de mais folga: o JSON de `ConsultaRecarga` tem uma lista de estações aninhadas, e um modelo "reasoning" como o `gpt-oss:120b` gasta parte do orçamento pensando antes de responder — com 512 tokens a saída saía truncada no meio do JSON (`OutputParserException: Invalid json output`, achado ao rodar `evals/run_evals.py` pela primeira vez com rede real). Ver Problema 4 em `docs/relatorio_evolucao.pdf`. |
| `top_p` | `0.95` (obrigatório desde esta revisão) | `src/chain/builder.py::build_llm` (padrão) | Normalmente fica a critério do padrão embutido em cada modelo no Ollama — que descobrimos **não ser garantidamente o mesmo valor** entre modelos (gpt-oss e nemotron, por exemplo, têm recomendações próprias dos criadores). Por isso, todo `ChatOllama` do projeto sempre define `top_p=0.95` explicitamente, isolando essa variável na comparação. |
| `format` | `"json"` somente na chain estruturada (`build_structured_chain`) | `src/chain/builder.py` | Garante JSON sintaticamente válido antes do `PydanticOutputParser` validar o schema (Aula 03). |

## 3. Como reproduzir a comparação

```bash
python -m evals.comparar_modelos
```

O script roda as mesmas 3 perguntas do domínio nos dois modelos e grava
`evals/resultados_comparacao_modelos.json` com resposta e latência de cada
um. A tabela da seção 4 abaixo já foi preenchida com os dados dessa rodada
(`evals/resultados_comparacao_modelos.json`) — rode de novo se quiser
atualizar os números.

## 4. Resultado da comparação

Dados da rodada atual, gravados em `evals/resultados_comparacao_modelos.json`,
já com `top_p=0.95` fixo para os dois modelos (ver seção 2).

| Critério | `gpt-oss:120b` | `nemotron-3-nano:30b` |
|---|---|---|
| Latência média (s) | **1,47 s** (0,94 / 1,56 / 1,91) | **22,79 s** (29,04 / 23,62 / 15,72) — cerca de 15× mais lento |
| Aderência ao escopo GoodWe | Total nas 3 perguntas. Segue à risca a regra do prompt de avisar o alerta da Estação 2 **proativamente em toda resposta**, mesmo na pergunta 1, que não pedia isso. | Total nas 3 perguntas (nenhum desvio de escopo), mas só avisa o alerta proativamente nas perguntas 2 e 3 — na pergunta 1 (sessões/consumo) não menciona a Estação 2, o que vai contra a regra `<regras>` de sempre informar alerta ativo. |
| Qualidade percebida das respostas (1–5) | **5** — respostas completas, bem estruturadas, sempre terminam a frase, e recomendam corretamente um eletricista credenciado em vez de dar conselho elétrico direto. | **4** — respostas completas e sem truncamento nesta rodada, mas com uma imprecisão na pergunta 2 (mistura o horário do pico previsto pela IA, 18h30, com o bloqueio via OCPP, que já estava ativo desde 14h10, dando a entender que o bloqueio só começaria às 18h) e a omissão do alerta na pergunta 1. |
| Recomendação de uso | Manter como modelo padrão do projeto — mais consistente com as regras do prompt e, nesta rodada, ordens de grandeza mais rápido. | Não recomendado para este caso de uso: ~23 s de latência média por resposta é incompatível com um assistente operacional em tempo real, independentemente da qualidade do texto gerado. |

### Observações da rodada (evidência em `evals/resultados_comparacao_modelos.json`)

- **Latência é o fator decisivo nesta rodada**: o `nemotron-3-nano:30b` levou
  entre 15,7 s e 29,0 s por resposta (média 22,8 s), contra 0,9 s–1,9 s do
  `gpt-oss:120b` (média 1,5 s) — uma diferença de ordem de grandeza que, por
  si só, já inviabiliza o `nemotron-3-nano:30b` para um assistente que
  responde em tempo real a um operador.
- **Sem truncamento nesta rodada**: diferente de execuções anteriores,
  nenhuma das 6 respostas (3 por modelo) foi cortada no meio da frase — os
  dois modelos concluíram o raciocínio dentro dos 512 tokens de
  `num_predict`.
- **Alerta proativo inconsistente**: o system prompt (`<regras>`) instrui a
  sempre informar um alerta ativo. O `gpt-oss:120b` cumpriu isso nas 3
  respostas; o `nemotron-3-nano:30b` só mencionou o alerta da Estação 2
  quando a pergunta já tocava no assunto (demanda/estações), não na pergunta
  sobre sessões e consumo.
- **Imprecisão do `nemotron-3-nano:30b` na pergunta 2**: a resposta mistura o
  horário do pico previsto pela IA (18h30) com o bloqueio de sessões da
  Estação 2, que já estava ativo desde as 14h10 por causa do alerta de
  sobretensão — dando a entender, incorretamente, que o bloqueio só passaria
  a valer às 18h.
- **Guardrail elétrico respeitado por ambos**: nenhum dos dois modelos deu
  instrução prática de manuseio elétrico — o `gpt-oss:120b` recomenda
  explicitamente um eletricista credenciado; o `nemotron-3-nano:30b`
  recomenda verificar o painel de controle e acionar o suporte técnico. Os
  dois escalam para um profissional em vez de orientar o operador a mexer no
  equipamento.

## 5. Observações

- A troca de modelo não exige mudar nenhuma outra parte da chain — é só o
  argumento `model=` de `build_llm()`, evidência direta do ganho de
  composição do LCEL (Aula 01): o mesmo `prompt | llm | parser` funciona
  com qualquer `ChatOllama`.
- Nenhum modelo local foi usado em nenhuma etapa deste projeto (nem para
  embeddings): todo o processamento de linguagem passa pelo Ollama Cloud,
  conforme exigido para esta sprint.
- A latência de ~23 s do `nemotron-3-nano:30b` nesta rodada pode ser efeito
  de fila ou *cold start* no Ollama Cloud, ou característica do próprio
  modelo — antes de descartá-lo definitivamente para outros usos, valeria
  rodar `python -m evals.comparar_modelos` de novo em outro horário para
  ver se o resultado se repete.
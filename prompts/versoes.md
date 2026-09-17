# Versionamento do system prompt — ChargeGrid Assistant

| Versão | Arquivo | O que mudou | Por quê | Ganho medido |
|---|---|---|---|---|
| v1 | `system_prompt_v1.md` | Baseline herdado das Sprints 1/2: bloco único de texto corrido, 8+ instruções misturadas (persona, regulação, pilares, regras de escopo, guardrails jurídicos/financeiros/elétricos, anti-jailbreak) sem separação por seção. | Era o `get_system_prompt()` de `chatbot.py` na Sprint 2, escrito antes de a turma ver context engineering (Aula 04). | Baseline de comparação — ver `docs/relatorio_modelos.md`. |
| v2 | `system_prompt_v2.md` | Reescrito com XML tagging (`<persona>`, `<escopo>`, `<regulamentacao>`, `<pilares>`, `<dados_operacionais>`, `<alertas>`, `<regras>`); instruções críticas de identidade/escopo repetidas no início (`<persona>`/`<escopo>`) **e** no fim (`<regras>`), técnica da Aula 04 para mitigar *context rot* (Liu et al., 2023 — "Lost in the Middle"); frases redundantes e de polidez removidas; instruções em forma imperativa. | Reduzir o risco de o modelo "esquecer" regras que ficam no meio de um bloco longo (base do *context rot*) e reforçar justamente as regras que os guardrails de código (Bloco C) não cobrem sozinhos — recusa de aconselhamento e anti-jailbreak também reforçados no próprio prompt como segunda camada de defesa. | ⚠️ **Pendente** — rode `python prompts/medir_tokens.py` (requer `pip install tiktoken`, já listado em `requirements.txt`) e cole aqui o "Redução: X%" impresso pelo script. O resultado também é gravado em `prompts/tokens_resultado.json`, que `docs/gerar_relatorio_evolucao.py` já lê automaticamente para preencher a tabela antes/depois do PDF. |

## Como reproduzir a medição

```bash
python prompts/medir_tokens.py
```

O script imprime o total de tokens de `system_prompt_v1.md` e de
`system_prompt_v2.md` (sem os placeholders `{dados_operacionais}`/`{alertas}`,
que têm tamanho variável) e a redução percentual — o mesmo procedimento da
Aula 04. Cole o resultado impresso na coluna "Ganho medido" acima e também na
tabela antes/depois de `docs/relatorio_evolucao.pdf`.

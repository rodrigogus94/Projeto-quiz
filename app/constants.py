from __future__ import annotations

EMPTY_QUESTION = {
    "question": "",
    "options": ["", "", "", ""],
    "correct": "A",
}

EXAM_FORMAT_HELP = """
**Formato do arquivo da prova (`.pdf`, `.md` ou `.markdown`, com gabarito — só o professor vê):**

**Múltipla escolha:**
```
Pergunta 1: Enunciado da questão?
Alternativa A (Vermelho): texto
Alternativa B (Azul): texto (CORRETA)
Alternativa C (Amarelo): texto
Alternativa D (Verde): texto
```

**Justificativa / dissertativa:**
```
Pergunta 2: Explique o conceito X. (JUSTIFICATIVA)
Gabarito: texto esperado na correção
```
ou use `Resposta esperada:` / `Tipo: Justificativa` / enunciado com "Justifique".

**Markdown (`.md` / `.markdown`):**
```
### Questão 1
Enunciado da questão?
A) alternativa A
B) alternativa B
C) alternativa C
D) alternativa D

**Resposta Correta: C**
```
"""

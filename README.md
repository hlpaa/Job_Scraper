# Job Scraper

Coleta vagas de estágio na Gupy, filtra por título e localização, e usa o Gemini para pontuar as que passam no filtro.

## Fluxo

```
Gupy API → corte duro (título + cidade) → SQLite → Gemini (nota 0–10) → banco atualizado
```

1. **Coleta** — busca vagas de estágio na Gupy pelos termos definidos em `scraper.TERMOS`
2. **Corte duro** — descarta títulos bloqueados (operador, auxiliar, etc.) e vagas fora de Recife/remoto
3. **Persistência** — salva no SQLite com `INSERT OR IGNORE` (sem duplicatas entre execuções)
4. **Pontuação** — envia cada vaga que passou o corte para o Gemini; salva nota, aprovação e motivo

## Estrutura

```
scraper.py   — coleta e filtro de vagas (Gupy API)
db.py        — schema SQLite e funções de acesso
agente.py    — pontuação via Gemini (nota 0–10, aprovada, motivo)
pipeline.py  — orquestrador: roda tudo em sequência
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Crie um arquivo `.env` na raiz com sua chave do [Google AI Studio](https://aistudio.google.com/apikey):

```
GEMINI_API_KEY=sua_chave_aqui
```

## Uso

```bash
python pipeline.py
```

Saída esperada:

```
[busca] dados: 87 vagas
...
412 vagas únicas coletadas
novas no banco: 7 | cortadas: {'localizacao': 3, 'titulo': 1} | passaram: 3

pontuando 3 vagas...
  9.5 V  Estágio em Desenvolvimento de Software / Data Mining
  8.5 V  Programa de Estágio Smarthis | 2026
  2.0 X  Estágio em Contabilidade: Dados e Inteligência Artificial
pontuação concluída: 3 ok | 0 erros
```

## Banco de dados

Arquivo `vagas.db` (SQLite, criado automaticamente). Colunas principais:

| Coluna | Descrição |
|---|---|
| `id` | ID da vaga na Gupy (PK) |
| `titulo`, `empresa`, `cidade` | Dados da vaga |
| `remoto` | 1 se remoto |
| `passou_corte` | 1 se passou o filtro de título/localização |
| `nota` | Float 0–10 atribuído pelo Gemini |
| `aprovada` | 1 se nota ≥ 6.0 e critérios técnicos satisfeitos |
| `motivo` | Explicação do Gemini ou motivo do corte duro |

## Limites do free tier Gemini

5 requisições/minuto. O pipeline aguarda 12 s entre chamadas automaticamente.

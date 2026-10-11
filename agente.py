"""Pontuação de vagas via Gemini: retorna nota, aprovada e motivo."""
import json
import os
import re

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

_SYSTEM_PROMPT = """Você é um avaliador de vagas de estágio para estudantes de computação ou engenharia.

APROVAR (aprovada: true):
- Atividade técnica real: programação, SQL, modelagem de dados, APIs, infraestrutura,
  redes, engenharia/ciência de dados, desenvolvimento de software, automação de testes.
- Perfil esperado: estudante de computação, engenharia de software, sistemas ou similar.

REJEITAR (aprovada: false):
- Função real é administrativa, comercial, contábil ou de suporte, mesmo que o título
  use "dados", "IA" ou "tecnologia" (ex: Excel/Power BI para RH ou vendas, estágio
  administrativo com sistema de apoio, contabilidade com menção superficial a dados).

Responda EXCLUSIVAMENTE com JSON válido, sem texto antes ou depois:
{"nota": <float 0.0–10.0>, "aprovada": <true|false>, "motivo": "<string máx 120 chars>"}

- nota: 0.0 a 10.0, onde 10 é perfeito para estudante de computação/engenharia.
- aprovada: true somente se nota >= 6.0 E critérios de aprovação satisfeitos.
- motivo: uma frase curta explicando a decisão."""

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


def _montar_prompt(vaga: dict) -> str:
    if vaga.get("remoto"):
        localizacao = "remoto"
    else:
        localizacao = vaga.get("cidade") or "não informada"

    linhas = [
        "Avalie a seguinte vaga de estágio:",
        "",
        f"Título: {vaga['titulo']}",
        f"Empresa: {vaga.get('empresa') or 'não informada'}",
        f"Localização: {localizacao}",
    ]
    if vaga.get("descricao"):
        linhas.append(f"Descrição: {vaga['descricao']}")
    linhas.append("")
    linhas.append("Retorne o JSON de avaliação.")
    return "\n".join(linhas)


def _parse_resposta(texto: str) -> dict:
    match = re.search(r'\{.*\}', texto, re.DOTALL)
    if not match:
        return {"nota": None, "aprovada": None, "motivo": "parse_error: sem JSON na resposta"}
    try:
        dados = json.loads(match.group())
    except json.JSONDecodeError as e:
        return {"nota": None, "aprovada": None, "motivo": f"parse_error: {e}"}

    nota = dados.get("nota")
    aprovada = dados.get("aprovada")
    motivo = dados.get("motivo", "")

    if not isinstance(nota, (int, float)) or not (0.0 <= nota <= 10.0):
        return {"nota": None, "aprovada": None, "motivo": "parse_error: nota inválida"}
    if not isinstance(aprovada, bool):
        return {"nota": None, "aprovada": None, "motivo": "parse_error: aprovada inválida"}

    return {"nota": float(nota), "aprovada": aprovada, "motivo": str(motivo)[:120]}


def pontuar_vaga(vaga: dict) -> dict:
    """Recebe uma linha do banco e retorna {'nota', 'aprovada', 'motivo'}."""
    try:
        resposta = _get_client().models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=_montar_prompt(vaga),
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM_PROMPT,
                temperature=0,
                max_output_tokens=150,
            ),
        )
        return _parse_resposta(resposta.text)
    except Exception as e:
        return {"nota": None, "aprovada": None, "motivo": f"erro_api: {e}"}

"""Coleta e filtragem de vagas de estágio na Gupy."""
import re
import time
import unicodedata

import requests

API_URL = "https://portal.gupy.io/api/job-search/jobs"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
LIMITE_PAGINA = 50

TERMOS = ["dados", "desenvolvedor", "programador", "infraestrutura", "sistemas", "software"]

TITULOS_BLOQUEADOS = [
    "operador",
    "operadora",
    "auxiliar",
    "assistente",
    "supervisor",
    "supervisora",
    "agente de relacionamento",
    "coordenador",
    "coordenadora",
    "trainee comercial",
    "vendedor",
    "vendedora",
    "atendente",
    "recepcionista",
]
CIDADE_ALVO = "recife"


def normalizar(texto: str | None) -> str:
    """Minúsculas e sem acentos, para comparação."""
    sem_acento = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return sem_acento.lower().strip()


REGEX_BLOQUEIO = re.compile(r"\b(" + "|".join(re.escape(normalizar(t)) for t in TITULOS_BLOQUEADOS) + r")\b")


def buscar_vagas(termo: str) -> list[dict]:
    """Busca todas as páginas de vagas de estágio para um termo."""
    vagas, offset = [], 0
    while True:
        resp = requests.get(
            API_URL,
            params={"jobName": termo, "type": "vacancy_type_internship", "limit": LIMITE_PAGINA, "offset": offset},
            headers=HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        corpo = resp.json()
        pagina = corpo.get("data", [])
        vagas.extend(pagina)
        offset += LIMITE_PAGINA
        if not pagina or offset >= corpo.get("pagination", {}).get("total", 0):
            return vagas
        time.sleep(0.5)


def coletar(termos: list[str]) -> dict[int, dict]:
    """Roda a busca para cada termo e deduplica por id."""
    vagas = {}
    for termo in termos:
        try:
            encontradas = buscar_vagas(termo)
        except (requests.exceptions.RequestException, ValueError) as e:
            print(f"[erro] busca por '{termo}' falhou: {e}")
            continue
        print(f"[busca] {termo}: {len(encontradas)} vagas")
        for v in encontradas:
            if v["id"] not in vagas:
                vagas[v["id"]] = {**v, "termos": []}
            vagas[v["id"]]["termos"].append(termo)
        time.sleep(0.5)
    return vagas


def corte_duro(vaga: dict) -> str | None:
    """Retorna o motivo do descarte, ou None se a vaga passa."""
    m = REGEX_BLOQUEIO.search(normalizar(vaga.get("name")))
    if m:
        return f"titulo: {m.group(1)}"
    if vaga.get("workplaceType") != "remote" and normalizar(vaga.get("city")) != CIDADE_ALVO:
        return "localizacao"
    return None

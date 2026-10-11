"""Acesso ao banco SQLite: schema, inserção e consulta de vagas."""
import sqlite3
from datetime import datetime, timezone


def conectar(caminho: str = "vagas.db") -> sqlite3.Connection:
    conn = sqlite3.connect(caminho)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def criar_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS vagas (
            id            INTEGER PRIMARY KEY,
            url           TEXT    NOT NULL,
            titulo        TEXT    NOT NULL,
            empresa       TEXT,
            cidade        TEXT,
            remoto        INTEGER NOT NULL CHECK (remoto IN (0, 1)),
            coletado_em   TEXT    NOT NULL,
            passou_corte  INTEGER NOT NULL CHECK (passou_corte IN (0, 1)),
            nota          REAL,
            aprovada      INTEGER CHECK (aprovada IN (0, 1) OR aprovada IS NULL),
            motivo        TEXT,
            rotulo_manual INTEGER CHECK (rotulo_manual IN (0, 1) OR rotulo_manual IS NULL)
        );

        CREATE INDEX IF NOT EXISTS idx_para_pontuar
            ON vagas (passou_corte, nota)
            WHERE passou_corte = 1 AND nota IS NULL;

        CREATE INDEX IF NOT EXISTS idx_aprovadas
            ON vagas (aprovada, coletado_em);
    """)


def inserir_vaga(
    conn: sqlite3.Connection,
    vaga: dict,
    passou: bool,
    motivo: str | None,
) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO vagas
            (id, url, titulo, empresa, cidade, remoto, coletado_em, passou_corte, motivo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            vaga["id"],
            f"https://portal.gupy.io/job/{vaga['id']}",
            vaga["name"],
            vaga.get("careerPageName"),
            vaga.get("city"),
            1 if vaga.get("workplaceType") == "remote" else 0,
            datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            1 if passou else 0,
            motivo,
        ),
    )


def buscar_para_pontuar(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM vagas WHERE passou_corte = 1 AND nota IS NULL"
    ).fetchall()
    return [dict(r) for r in rows]


def salvar_pontuacao(
    conn: sqlite3.Connection,
    id: int,
    nota: float | None,
    aprovada: bool | None,
    motivo: str,
) -> None:
    conn.execute(
        "UPDATE vagas SET nota = ?, aprovada = ?, motivo = ? WHERE id = ?",
        (nota, (1 if aprovada else 0) if aprovada is not None else None, motivo, id),
    )

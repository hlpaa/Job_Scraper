"""Ponto de entrada do MVP: coleta → corte duro → persistência → pontuação."""
import time
from collections import Counter

import agente
import db
import scraper

_INTERVALO_API = 12  # 5 req/min no free tier → 1 req/12 s


def main() -> None:
    conn = db.conectar()
    db.criar_schema(conn)

    vagas = scraper.coletar(scraper.TERMOS)
    print(f"{len(vagas)} vagas únicas coletadas")

    novas, novas_passaram, motivos = 0, 0, Counter()
    for v in vagas.values():
        motivo = scraper.corte_duro(v)
        passou = motivo is None
        ja_existia = conn.execute("SELECT 1 FROM vagas WHERE id = ?", (v["id"],)).fetchone() is not None
        db.inserir_vaga(conn, v, passou=passou, motivo=motivo)
        if not ja_existia:
            novas += 1
            if passou:
                novas_passaram += 1
            else:
                motivos[motivo.split(":")[0]] += 1

    conn.commit()
    print(f"novas no banco: {novas} | cortadas: {dict(motivos)} | passaram: {novas_passaram}")

    # pontuação via Gemini
    para_pontuar = db.buscar_para_pontuar(conn)
    print(f"\npontuando {len(para_pontuar)} vagas...")
    aprovadas, erros = 0, 0
    for i, v in enumerate(para_pontuar):
        if i > 0:
            time.sleep(_INTERVALO_API)
        r = agente.pontuar_vaga(v)
        db.salvar_pontuacao(conn, v["id"], r["nota"], r["aprovada"], r["motivo"])
        conn.commit()
        if r["nota"] is None:
            erros += 1
            print(f"  ERR  {v['titulo'][:60]}")
        else:
            flag = "V" if r["aprovada"] else "X"
            print(f"  {r['nota']:.1f} {flag}  {v['titulo'][:60]}")
    print(f"pontuação concluída: {len(para_pontuar) - erros} ok | {erros} erros")


if __name__ == "__main__":
    main()

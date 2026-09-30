"""Extrai os CSVs de vendas (histórico + incremental) e carrega crus no
DuckDB, na camada raw.

Ponto central do exercício: lemos cada arquivo PELO NOME das colunas
(pandas.read_csv usa o header), não por posição — por isso é indiferente
que os dois arquivos tenham nomes de coluna e ordem diferentes entre si.
Cada tabela raw espelha fielmente o schema da sua fonte; a reconciliação
de nomenclatura fica para a camada de staging (ver transform.sql).
"""

from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "warehouse" / "workshop.duckdb"
RAW_CSV = ROOT / "data" / "raw" / "vendas_lojas.csv"
INCOMING_CSV = ROOT / "data" / "incoming" / "vendas_lojas_recentes.csv"


def carregar_csv_em_raw(con, csv_path, tabela_destino):
    df = pd.read_csv(csv_path, dtype=str)  # dtype=str: staging cuida da tipagem
    con.register("_tmp_df", df)
    con.execute(f"CREATE OR REPLACE TABLE {tabela_destino} AS SELECT * FROM _tmp_df")
    con.unregister("_tmp_df")
    print(f"[extract_csv] {csv_path.name} ({len(df)} linhas) -> {tabela_destino}")


def main():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH))
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")

    carregar_csv_em_raw(con, RAW_CSV, "raw.vendas_historico")
    carregar_csv_em_raw(con, INCOMING_CSV, "raw.vendas_recentes")

    con.close()


if __name__ == "__main__":
    main()

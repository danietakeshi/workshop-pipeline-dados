"""Orquestra o pipeline completo em um único comando:

  1. extract_csv     -> raw.vendas_historico, raw.vendas_recentes
  2. extract_weather  -> raw.clima
  3. transform.sql    -> stg_vendas, stg_clima, mart_vendas_clima, ...

Uso: python scripts/run_pipeline.py
"""

import subprocess
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
DB_PATH = ROOT / "warehouse" / "workshop.duckdb"
TRANSFORM_SQL_PATH = SCRIPTS_DIR / "transform.sql"


def rodar_script_python(nome_arquivo):
    print(f"\n{'=' * 60}\n>>> {nome_arquivo}\n{'=' * 60}")
    resultado = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / nome_arquivo)],
        check=True,
    )
    return resultado


def rodar_transformacoes():
    print(f"\n{'=' * 60}\n>>> transform.sql\n{'=' * 60}")
    sql = TRANSFORM_SQL_PATH.read_text(encoding="utf-8")
    # DuckDB lida bem com comentários '--' dentro de um statement; só
    # precisamos descartar os pedaços vazios que sobram entre statements.
    statements = [s.strip() for s in sql.split(";") if s.strip()]

    con = duckdb.connect(str(DB_PATH))
    for statement in statements:
        con.execute(statement)
    con.close()
    print("[transform] staging e marts atualizados com sucesso")


def mostrar_resumo():
    con = duckdb.connect(str(DB_PATH), read_only=True)
    print(f"\n{'=' * 60}\n>>> resumo do warehouse\n{'=' * 60}")
    tabelas = con.execute("""
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
        ORDER BY table_schema, table_name
    """).fetchall()
    for schema, tabela in tabelas:
        nome_completo = f"{schema}.{tabela}" if schema != "main" else tabela
        count = con.execute(f"SELECT COUNT(*) FROM {nome_completo}").fetchone()[0]
        print(f"  {nome_completo:35s} {count:>6d} linhas")
    con.close()


def main():
    rodar_script_python("extract_csv.py")
    rodar_script_python("extract_weather.py")
    rodar_transformacoes()
    mostrar_resumo()
    print(f"\nPipeline concluído. Banco DuckDB em: {DB_PATH}")


if __name__ == "__main__":
    main()

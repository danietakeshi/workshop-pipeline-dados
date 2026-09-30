"""Script de apoio para o bloco 'Extração — arquivos estáticos' do workshop.

Mostra, ao vivo, por que ler um CSV POR POSIÇÃO de coluna é uma armadilha
quando a fonte muda de schema — e por que ler POR NOME de coluna (header)
resolve o problema. Rode este script depois de gerar os CSVs mockados.

Uso: python scripts/demo_schema_drift.py
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HISTORICO = ROOT / "data" / "raw" / "vendas_lojas.csv"
RECENTES = ROOT / "data" / "incoming" / "vendas_lojas_recentes.csv"


def extrair_por_posicao(path, n_linhas=3):
    """JEITO ERRADO: assume que a coluna 0 é sempre data, a 1 é sempre
    loja etc. Funciona no arquivo histórico, mas quebra silenciosamente
    no arquivo incremental porque a ordem das colunas mudou."""
    print(f"\n--- extração POR POSIÇÃO em {path.name} ---")
    with open(path, encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        print(f"header real do arquivo: {header}")
        for i, row in enumerate(reader):
            if i >= n_linhas:
                break
            # Pressupõe a ordem do schema histórico: data, loja, cidade, cliente_id...
            print(f"  linha {i}: coluna[0] (deveria ser 'data')={row[0]!r}  "
                  f"coluna[1] (deveria ser 'loja')={row[1]!r}")


def extrair_por_header(path, n_linhas=3):
    """JEITO CERTO: lê pelo nome da coluna. Não importa a ordem nem quais
    outras colunas existem — só precisamos saber os nomes que esperamos."""
    print(f"\n--- extração POR HEADER em {path.name} ---")
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= n_linhas:
                break
            data = row.get("data_venda") or row.get("dt_venda")
            loja = row.get("loja_id") or row.get("id_loja")
            print(f"  linha {i}: data={data!r}  loja={loja!r}")


if __name__ == "__main__":
    print("=" * 70)
    print("Arquivo HISTÓRICO (schema canônico) -- os dois métodos funcionam")
    print("=" * 70)
    extrair_por_posicao(HISTORICO)
    extrair_por_header(HISTORICO)

    print()
    print("=" * 70)
    print("Arquivo INCREMENTAL (schema com colunas renomeadas/reordenadas)")
    print("Repare: por posição o resultado sai TROCADO. Por header, continua certo.")
    print("=" * 70)
    extrair_por_posicao(RECENTES)
    extrair_por_header(RECENTES)

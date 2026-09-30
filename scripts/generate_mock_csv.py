"""Gera os CSVs mockados de vendas da GeloDados usados no workshop.

Produz dois arquivos que representam a MESMA fonte de dados em dois momentos:

1. data/raw/vendas_lojas.csv
   Carga historica, com o schema "canonico" (nomes de coluna completos).
   Contem sujeira proposital (datas em formato misto, nulos, duplicatas,
   um outlier de venda) para o bloco de limpeza de dados do workshop.

2. data/incoming/vendas_lojas_recentes.csv
   Carga incremental "mais recente", exportada por uma versao nova do
   sistema de origem: mesmas informacoes, porem com colunas RENOMEADAS
   (convencao abreviada) e em ORDEM DIFERENTE. Usada para demonstrar por
   que extrair CSV por posicao de coluna e uma armadilha (schema drift).

Rodar de novo sempre gera os mesmos arquivos (seed fixa) para que o
comportamento no dia do workshop seja previsivel.
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

SEED = 42
random.seed(SEED)

ROOT = Path(__file__).resolve().parent.parent
RAW_PATH = ROOT / "data" / "raw" / "vendas_lojas.csv"
INCOMING_PATH = ROOT / "data" / "incoming" / "vendas_lojas_recentes.csv"

# Janela histórica e janela incremental são contíguas e ficam totalmente no
# passado em relação a hoje, para garantir que a API de clima (Open-Meteo
# archive) já tenha dado final disponível (sem lag de reanálise) na data do
# workshop.
HIST_START = date(2026, 6, 1)
HIST_END = date(2026, 8, 27)       # 88 dias de histórico
INCREMENTAL_START = date(2026, 8, 28)
INCREMENTAL_END = date(2026, 9, 1)  # 5 dias de carga incremental

LOJAS = [
    ("LJ01", "Sao Paulo"),
    ("LJ02", "Rio de Janeiro"),
    ("LJ03", "Curitiba"),
    ("LJ04", "Fortaleza"),
    ("LJ05", "Porto Alegre"),
]

PRIMEIROS_NOMES = [
    "Ana", "Bruno", "Carla", "Daniel", "Eduarda", "Felipe", "Gabriela",
    "Henrique", "Isabela", "Joao", "Karina", "Lucas", "Mariana", "Nathan",
    "Otavio", "Patricia", "Rafael", "Sabrina", "Thiago", "Vanessa",
]
SOBRENOMES = [
    "Silva", "Santos", "Oliveira", "Souza", "Rodrigues", "Ferreira",
    "Almeida", "Pereira", "Lima", "Carvalho", "Gomes", "Martins",
]

PRODUTOS_SABORES = {
    "Picole": (["Chocolate", "Morango", "Limao", "Coco"], (4.50, 6.50)),
    "Sorvete Pote": (["Chocolate", "Morango", "Baunilha", "Napolitano"], (18.00, 32.00)),
    "Milkshake": (["Chocolate", "Morango", "Baunilha", "Ovomaltine"], (12.00, 16.00)),
    "Agua de Coco": (["Coco"], (6.00, 9.00)),
}

FORMAS_PAGAMENTO = ["pix"] * 5 + ["cartao"] * 4 + ["dinheiro"] * 1  # pix mais comum

N_CLIENTES = 150
TRANSACOES_POR_LOJA_DIA = (6, 14)  # min, max


def gerar_clientes(n):
    clientes = []
    for i in range(1, n + 1):
        nome = f"{random.choice(PRIMEIROS_NOMES)} {random.choice(SOBRENOMES)}"
        idade = random.randint(16, 72)
        genero = random.choices(["F", "M", "Outro"], weights=[48, 48, 4])[0]
        clientes.append({
            "cliente_id": f"CLI{i:05d}",
            "nome_cliente": nome,
            "idade_cliente": idade,
            "genero_cliente": genero,
        })
    return clientes


def gerar_transacao(dia, loja_id, cidade, clientes):
    cliente = random.choice(clientes)
    produto = random.choice(list(PRODUTOS_SABORES.keys()))
    sabores, (preco_min, preco_max) = PRODUTOS_SABORES[produto]
    sabor = random.choice(sabores)
    unidades = random.randint(1, 5)
    preco_unitario = round(random.uniform(preco_min, preco_max), 2)
    receita = round(unidades * preco_unitario, 2)
    forma_pagamento = random.choice(FORMAS_PAGAMENTO)

    return {
        "data_venda": dia.isoformat(),
        "loja_id": loja_id,
        "cidade": cidade,
        "cliente_id": cliente["cliente_id"],
        "nome_cliente": cliente["nome_cliente"],
        "idade_cliente": cliente["idade_cliente"],
        "genero_cliente": cliente["genero_cliente"],
        "produto": produto,
        "sabor": sabor,
        "unidades_vendidas": unidades,
        "preco_unitario": preco_unitario,
        "receita_brl": receita,
        "forma_pagamento": forma_pagamento,
    }


def gerar_transacoes_periodo(inicio, fim, clientes):
    transacoes = []
    dia = inicio
    while dia <= fim:
        for loja_id, cidade in LOJAS:
            n_transacoes = random.randint(*TRANSACOES_POR_LOJA_DIA)
            for _ in range(n_transacoes):
                transacoes.append(gerar_transacao(dia, loja_id, cidade, clientes))
        dia += timedelta(days=1)
    return transacoes


def sujar_dados(transacoes):
    """Aplica sujeira proposital: datas em formato misto, nulos, duplicatas
    e um outlier de venda. Só usado na carga histórica."""

    # ~5% das linhas com data em dd/mm/yyyy em vez de yyyy-mm-dd
    for t in random.sample(transacoes, k=max(1, len(transacoes) // 20)):
        y, m, d = t["data_venda"].split("-")
        t["data_venda"] = f"{d}/{m}/{y}"

    # ~3% das linhas com genero ou idade faltando
    for t in random.sample(transacoes, k=max(1, len(transacoes) // 33)):
        if random.random() < 0.5:
            t["genero_cliente"] = ""
        else:
            t["idade_cliente"] = ""

    # 10 linhas duplicadas (simula reprocessamento/erro de extração dupla)
    duplicatas = random.sample(transacoes, k=10)
    transacoes.extend(dict(t) for t in duplicatas)

    # 1 outlier claro de venda (erro de digitação no PDV)
    outlier = random.choice(transacoes)
    outlier["unidades_vendidas"] = 500
    outlier["receita_brl"] = round(500 * outlier["preco_unitario"], 2)

    random.shuffle(transacoes)
    return transacoes


CANONICAL_COLUMNS = [
    "data_venda", "loja_id", "cidade", "cliente_id", "nome_cliente",
    "idade_cliente", "genero_cliente", "produto", "sabor",
    "unidades_vendidas", "preco_unitario", "receita_brl", "forma_pagamento",
]

# Mapeamento canonico -> nomenclatura "nova" (schema drift), e a ordem em
# que as colunas aparecem no arquivo incremental.
RENAME_MAP = {
    "data_venda": "dt_venda",
    "loja_id": "id_loja",
    "cidade": "uf_cidade",
    "cliente_id": "id_cliente",
    "nome_cliente": "nm_cliente",
    "idade_cliente": "idade",
    "genero_cliente": "genero",
    "produto": "categoria_produto",
    "sabor": "sabor_item",
    "unidades_vendidas": "qtd_vendida",
    "preco_unitario": "vl_unitario",
    "receita_brl": "vl_total",
    "forma_pagamento": "tipo_pagamento",
}

INCOMING_COLUMN_ORDER = [
    "id_cliente", "nm_cliente", "dt_venda", "id_loja", "uf_cidade",
    "categoria_produto", "sabor_item", "qtd_vendida", "vl_unitario",
    "vl_total", "tipo_pagamento", "idade", "genero",
]


def escrever_csv(path, linhas, colunas):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=colunas)
        writer.writeheader()
        writer.writerows(linhas)


def main():
    clientes = gerar_clientes(N_CLIENTES)

    # --- Carga histórica (schema canônico, com sujeira) ---
    historico = gerar_transacoes_periodo(HIST_START, HIST_END, clientes)
    historico = sujar_dados(historico)
    escrever_csv(RAW_PATH, historico, CANONICAL_COLUMNS)
    print(f"[historico] {len(historico)} linhas -> {RAW_PATH}")

    # --- Carga incremental (schema com nomenclatura/ordem diferentes) ---
    recentes = gerar_transacoes_periodo(INCREMENTAL_START, INCREMENTAL_END, clientes)
    recentes_renomeadas = [
        {RENAME_MAP[k]: v for k, v in t.items()} for t in recentes
    ]
    escrever_csv(INCOMING_PATH, recentes_renomeadas, INCOMING_COLUMN_ORDER)
    print(f"[incremental] {len(recentes_renomeadas)} linhas -> {INCOMING_PATH}")


if __name__ == "__main__":
    main()

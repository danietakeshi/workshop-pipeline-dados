# Construindo um Pipeline de Dados — da Ingestão à Análise

Workshop da Semana Acadêmica de Ciência da Computação — PUC-SP (PUCTech), 06/10/2026.

Case: **GeloDados**, uma rede fictícia de 5 lojas de sorvete/bebida gelada. O time comercial exporta vendas diárias em CSV, mas ninguém sabe dizer se o **clima** influencia as vendas — essa informação não existe internamente, precisa vir de uma **API pública** (Open-Meteo). Sua missão: construir o pipeline que junta os dois mundos e responde:

> *"Vendemos mais quando está mais quente? Em qual loja o efeito é mais forte?"*

O plano completo (contexto, decisões, roteiro da aula) está em [`PLAN.md`](PLAN.md).

---

## Antes de começar

Veja [`SETUP.md`](SETUP.md) para os pré-requisitos (Python, Docker, Git). Idealmente isso já foi instalado **antes** do dia do workshop.

---

## Arquitetura

```
CSV (histórico)  ─┐
CSV (incremental)─┼─> extract_csv.py    ─┐
Open-Meteo API   ──> extract_weather.py ─┼─> DuckDB (raw -> staging -> mart) -> Metabase
                                          ┘
```

- **raw** — dado bruto, cada tabela espelha fielmente sua fonte
- **staging** — limpeza, tipagem, reconciliação de schema entre as duas fontes de vendas
- **mart** — dado agregado e pronto para o Metabase consumir

Detalhes de schema e decisões de modelagem: ver seções 3 e 5 do [`PLAN.md`](PLAN.md).

---

## Passo a passo

### 1. Clonar o repositório

```bash
git clone <url-do-repositorio>
cd workshop-pipeline-dados
```

### 2. Ambiente Python

```bash
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# Windows (Git Bash) / Linux / Mac
source .venv/Scripts/activate   # ou .venv/bin/activate no Linux/Mac

pip install -r requirements.txt
```

### 3. (Opcional) Gerar os CSVs de novo

Os CSVs já estão commitados em `data/raw/` e `data/incoming/`, então este passo não é obrigatório. Mas se quiser ver como eles são gerados (ou gerar um volume diferente):

```bash
python scripts/generate_mock_csv.py
```

### 4. O problema da leitura por posição (schema drift)

Antes de rodar o pipeline de verdade, veja ao vivo por que ler CSV **por posição de coluna** é perigoso quando a fonte muda de schema:

```bash
python scripts/demo_schema_drift.py
```

Repare que `data/incoming/vendas_lojas_recentes.csv` tem as mesmas informações que o histórico, só que com **colunas renomeadas e em outra ordem** — simulando uma atualização no sistema de origem. Ler por header (nome da coluna) resolve o problema; ler por posição, não.

### 5. Rodar o pipeline completo

```bash
python scripts/run_pipeline.py
```

Isso executa, em sequência:
1. `extract_csv.py` — carrega os dois CSVs crus em `raw.vendas_historico` / `raw.vendas_recentes`
2. `extract_weather.py` — busca o clima histórico das 5 cidades na Open-Meteo e carrega em `raw.clima` (se a API estiver fora do ar, usa automaticamente o cache em `data/cache/weather_snapshot.json`)
3. `transform.sql` — reconcilia as duas fontes de vendas, limpa os dados e monta as tabelas de mart

Ao final, o script imprime a contagem de linhas de cada tabela. O banco fica em `warehouse/workshop.duckdb`.

Tabelas geradas:

| Tabela | Camada | O que é |
|---|---|---|
| `raw.vendas_historico`, `raw.vendas_recentes`, `raw.clima` | raw | espelho das fontes, sem transformação |
| `stg_vendas` | staging | vendas unificadas, tipadas, sem duplicatas, com flag de outlier |
| `stg_clima` | staging | clima tipado |
| `mart_vendas_clima` | mart | vendas agregadas por dia/loja + clima do dia + faixa de temperatura |
| `mart_sabor_temperatura` | mart | unidades vendidas por sabor x faixa de temperatura |
| `mart_clientes` | mart | ticket médio e loja favorita por cliente |

### 6. Subir o Metabase

```bash
docker compose up -d --build
```

Na primeira vez isso builda uma imagem própria do Metabase (ver `metabase/Dockerfile`) e baixa a imagem base + o metabase.jar + o driver do DuckDB — pode demorar alguns minutos. Depois disso, `docker compose up -d` sozinho já reaproveita a imagem.

> **Por que uma imagem própria, e não `metabase/metabase:latest` direto?** A imagem oficial é baseada em Alpine (musl libc). O driver nativo do DuckDB é compilado para glibc e **trava a JVM com SIGSEGV** assim que é carregado em Alpine — não é algo que dê pra contornar instalando `libstdc++`/`gcompat` (testamos). `metabase/Dockerfile` resolve isso rodando o Metabase sobre `eclipse-temurin:25-jre`, que já usa uma base Debian com glibc de verdade.

Acesse http://localhost:3000, crie sua conta de admin local e pule a etapa de conectar um banco (vamos fazer isso manualmente a seguir).

### 7. Conectar o Metabase ao DuckDB

No Metabase: **Admin settings → Databases → Add database**

- Database type: **DuckDB**
- Database file: `/data/workshop.duckdb`

  (`/data` é o `warehouse/` do projeto, montado dentro do container pelo `docker-compose.yml`)

Se o tipo **DuckDB** não aparecer na lista, o build da imagem pode ter falhado — rode `docker compose build --no-cache metabase` e confira o log.

### 8. Montar o dashboard

Sugestão de 3 perguntas para montar ao vivo (mais detalhes no `PLAN.md`, seção 8):

1. **Receita total por cidade** — bar chart a partir de `mart_vendas_clima`
2. **Receita diária vs. temperatura máxima** — a pergunta central do case
3. **Receita média por faixa de temperatura, por loja** — resposta direta, usando a coluna `faixa_temperatura`

Stretch goals (se sobrar tempo): `mart_sabor_temperatura` (sabor mais vendido por clima) e `mart_clientes` (ticket médio por cliente/loja).

---

## Estrutura do repositório

```
├── PLAN.md                          # plano detalhado do workshop
├── README.md                        # este arquivo
├── SETUP.md                         # pré-requisitos, enviar antes do evento
├── requirements.txt
├── docker-compose.yml
├── data/
│   ├── raw/vendas_lojas.csv                 # histórico (schema canônico)
│   ├── incoming/vendas_lojas_recentes.csv   # incremental (schema drift proposital)
│   └── cache/weather_snapshot.json          # fallback offline da API de clima
├── scripts/
│   ├── generate_mock_csv.py
│   ├── extract_csv.py
│   ├── extract_weather.py
│   ├── transform.sql
│   ├── run_pipeline.py
│   └── demo_schema_drift.py
├── metabase/Dockerfile               # imagem custom (Debian/glibc) com o driver DuckDB
└── warehouse/                        # workshop.duckdb gerado pelo pipeline (não commitado)
```

---

## Troubleshooting

| Problema | Solução |
|---|---|
| API da Open-Meteo fora do ar / wifi instável | `extract_weather.py` cai automaticamente para `data/cache/weather_snapshot.json` |
| Metabase não lista "DuckDB" como tipo de banco | Rode `docker compose build --no-cache metabase` e confira o log do build |
| Erro de "incompatible file format" no Metabase | A versão do `duckdb` no `requirements.txt` precisa bater com a versão do driver embutido no `metabase/Dockerfile` (hoje, DuckDB 1.5.5) |
| Metabase trava/reinicia sozinho ao adicionar o banco DuckDB | Sintoma de estar usando `metabase/metabase:latest` (Alpine) em vez da imagem custom — confira se o `docker-compose.yml` está usando `build: ./metabase` |
| `docker compose up --build` demorando na primeira vez | Normal, baixa a base Java + o metabase.jar (~500MB) — faça isso com antecedência |

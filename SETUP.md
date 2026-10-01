# Pré-requisitos — fazer ANTES do dia 06/10

Para aproveitar bem as 2 horas de workshop, pedimos que cada participante chegue com o ambiente já pronto. Leva uns 10-15 minutos.

## 1. Instalar

- **Python 3.11 ou superior** — https://www.python.org/downloads/
- **Git** — https://git-scm.com/downloads
- **Docker Desktop** — https://www.docker.com/products/docker-desktop/
  - Depois de instalar, **abra o Docker Desktop pelo menos uma vez** e espere ele terminar de iniciar (ícone da baleia fica "parado", sem animação de loading)

## 2. Clonar o repositório e preparar o ambiente Python

```bash
git clone https://github.com/danietakeshi/workshop-pipeline-dados.git
cd workshop-pipeline-dados

python -m venv .venv
source .venv/Scripts/activate   # Windows (Git Bash) — no PowerShell: .venv\Scripts\Activate.ps1
                                  # Linux/Mac: source .venv/bin/activate

pip install -r requirements.txt
```

Teste se funcionou:

```bash
python scripts/run_pipeline.py
```

Se aparecer uma tabela de resumo no final com várias linhas em `mart_*`, está tudo certo.

## 3. Subir e testar o Metabase

```bash
docker compose up -d --build
```

Isso builda uma imagem própria do Metabase (ver `metabase/Dockerfile`) — a primeira vez demora alguns minutos porque baixa a base Java, o metabase.jar e o driver do DuckDB. (Usamos uma imagem própria porque a oficial `metabase/metabase:latest` é Alpine e trava com o driver do DuckDB — detalhes no README.)

Abra http://localhost:3000 no navegador — se a tela de setup do Metabase aparecer, está tudo pronto. Pode derrubar de novo com `docker compose down` (os dados não são perdidos, a gente sobe tudo de novo no dia do evento).

## Checklist final

- [ ] Python 3.11+ instalado (`python --version`)
- [ ] Git instalado (`git --version`)
- [ ] Docker Desktop instalado e aberto pelo menos uma vez
- [ ] Repositório clonado
- [ ] `pip install -r requirements.txt` rodou sem erro
- [ ] `python scripts/run_pipeline.py` rodou sem erro
- [ ] `docker compose up -d --build` sobe e http://localhost:3000 abre

Qualquer problema nesse checklist, é melhor resolver antes do dia — no evento vamos ter pouco tempo e wifi compartilhado entre todo mundo.

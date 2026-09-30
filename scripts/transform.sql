-- Transformação: raw -> staging -> mart
--
-- Rodar depois de extract_csv.py e extract_weather.py terem populado o
-- schema `raw` (raw.vendas_historico, raw.vendas_recentes, raw.clima).
--
-- staging: reconcilia as duas fontes de vendas (schema drift) em um único
-- schema canônico, corrige tipos e remove duplicatas exatas.
-- mart: agrega vendas por dia/loja e junta com o clima do dia, já pronto
-- para o Metabase consumir.


-- =====================================================================
-- STAGING — vendas
-- =====================================================================
-- raw.vendas_historico e raw.vendas_recentes têm nomes de coluna e ordem
-- diferentes (schema drift proposital). Aqui fazemos o rename explícito
-- de cada fonte para o schema canônico antes do UNION ALL — é o único
-- lugar do pipeline onde essa tradução acontece.

CREATE OR REPLACE TABLE stg_vendas AS
WITH historico_renomeado AS (
    SELECT
        data_venda,
        loja_id,
        cidade,
        cliente_id,
        nome_cliente,
        idade_cliente,
        genero_cliente,
        produto,
        sabor,
        unidades_vendidas,
        preco_unitario,
        receita_brl,
        forma_pagamento
    FROM raw.vendas_historico
),
recentes_renomeado AS (
    -- mesma fonte de dado, nomenclatura diferente (dt_venda, id_loja, vl_total...)
    -- -- reconciliado aqui para o schema canônico
    SELECT
        dt_venda        AS data_venda,
        id_loja         AS loja_id,
        uf_cidade       AS cidade,
        id_cliente      AS cliente_id,
        nm_cliente      AS nome_cliente,
        idade           AS idade_cliente,
        genero          AS genero_cliente,
        categoria_produto AS produto,
        sabor_item      AS sabor,
        qtd_vendida     AS unidades_vendidas,
        vl_unitario     AS preco_unitario,
        vl_total        AS receita_brl,
        tipo_pagamento  AS forma_pagamento
    FROM raw.vendas_recentes
),
unificado AS (
    SELECT DISTINCT * FROM historico_renomeado   -- remove duplicatas exatas
    UNION ALL
    SELECT DISTINCT * FROM recentes_renomeado
)
SELECT
    -- data_venda chega em dois formatos (YYYY-MM-DD ou DD/MM/YYYY) por causa
    -- da sujeira proposital no arquivo histórico
    CASE
        WHEN data_venda LIKE '____-__-__' THEN CAST(data_venda AS DATE)
        WHEN data_venda LIKE '__/__/____' THEN CAST(STRPTIME(data_venda, '%d/%m/%Y') AS DATE)
    END AS data_venda,
    loja_id,
    cidade,
    cliente_id,
    NULLIF(nome_cliente, '') AS nome_cliente,
    TRY_CAST(NULLIF(idade_cliente, '') AS INTEGER) AS idade_cliente,
    NULLIF(genero_cliente, '') AS genero_cliente,
    produto,
    sabor,
    CAST(unidades_vendidas AS INTEGER) AS unidades_vendidas,
    CAST(preco_unitario AS DOUBLE) AS preco_unitario,
    CAST(receita_brl AS DOUBLE) AS receita_brl,
    forma_pagamento,
    -- outlier de venda (ex.: erro de digitação no PDV) é mantido, não
    -- descartado, mas fica sinalizado para quem for analisar decidir o que fazer
    CAST(unidades_vendidas AS INTEGER) > 50 AS unidades_suspeitas
FROM unificado;


-- =====================================================================
-- STAGING — clima
-- =====================================================================

CREATE OR REPLACE TABLE stg_clima AS
SELECT
    cidade,
    CAST(data AS DATE) AS data,
    CAST(temp_max_c AS DOUBLE) AS temp_max_c,
    CAST(temp_min_c AS DOUBLE) AS temp_min_c,
    CAST(precipitacao_mm AS DOUBLE) AS precipitacao_mm
FROM raw.clima;


-- =====================================================================
-- MART — vendas diárias por loja + clima do dia
-- =====================================================================
-- Ajuste de grão: vendas está em nível de transação, clima está em nível
-- de dia/cidade. Agregamos vendas para o grão dia/loja antes do join.

CREATE OR REPLACE TABLE mart_vendas_clima AS
SELECT
    v.data_venda,
    v.loja_id,
    v.cidade,
    COUNT(*) AS qtd_transacoes,
    COUNT(DISTINCT v.cliente_id) AS clientes_distintos,
    SUM(v.unidades_vendidas) AS unidades_vendidas,
    SUM(v.receita_brl) AS receita_total_brl,
    ROUND(AVG(v.receita_brl), 2) AS ticket_medio_brl,
    c.temp_max_c,
    c.temp_min_c,
    c.precipitacao_mm,
    CASE
        WHEN c.temp_max_c < 20 THEN '< 20C'
        WHEN c.temp_max_c < 28 THEN '20-28C'
        ELSE '> 28C'
    END AS faixa_temperatura
FROM stg_vendas v
LEFT JOIN stg_clima c
    ON v.cidade = c.cidade AND v.data_venda = c.data
GROUP BY 1, 2, 3, c.temp_max_c, c.temp_min_c, c.precipitacao_mm;


-- =====================================================================
-- MART — sabor vendido por faixa de temperatura (stretch: dashboard #4)
-- =====================================================================

CREATE OR REPLACE TABLE mart_sabor_temperatura AS
SELECT
    v.produto,
    v.sabor,
    CASE
        WHEN c.temp_max_c < 20 THEN '< 20C'
        WHEN c.temp_max_c < 28 THEN '20-28C'
        ELSE '> 28C'
    END AS faixa_temperatura,
    SUM(v.unidades_vendidas) AS unidades_vendidas,
    SUM(v.receita_brl) AS receita_total_brl
FROM stg_vendas v
LEFT JOIN stg_clima c
    ON v.cidade = c.cidade AND v.data_venda = c.data
GROUP BY 1, 2, 3;


-- =====================================================================
-- MART — ticket médio por cliente e loja (stretch: dashboard #5)
-- =====================================================================

CREATE OR REPLACE TABLE mart_clientes AS
WITH compras_por_loja AS (
    SELECT cliente_id, loja_id, COUNT(*) AS qtd
    FROM stg_vendas
    GROUP BY cliente_id, loja_id
),
loja_favorita AS (
    SELECT cliente_id, loja_id AS loja_favorita
    FROM compras_por_loja
    QUALIFY ROW_NUMBER() OVER (PARTITION BY cliente_id ORDER BY qtd DESC) = 1
)
SELECT
    v.cliente_id,
    ANY_VALUE(v.nome_cliente) AS nome_cliente,
    lf.loja_favorita,
    COUNT(*) AS qtd_compras,
    SUM(v.receita_brl) AS receita_total_brl,
    ROUND(AVG(v.receita_brl), 2) AS ticket_medio_brl
FROM stg_vendas v
JOIN loja_favorita lf ON lf.cliente_id = v.cliente_id
GROUP BY v.cliente_id, lf.loja_favorita;

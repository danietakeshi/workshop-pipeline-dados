"""Extrai o clima histórico diário das 5 cidades da GeloDados via Open-Meteo
e carrega cru no DuckDB, na camada raw.

Duas chamadas por cidade:
  1. Geocoding API  -> converte nome da cidade em lat/long
     (usamos coordenadas fixas como fallback, já que são só 5 cidades
     conhecidas — mas fazemos a chamada real para ensinar o padrão)
  2. Archive API     -> série diária de temperatura min/max e precipitação

Se a rede falhar (ex.: wifi do campus instável), cai automaticamente para
o snapshot em cache (data/cache/weather_snapshot.json), para a aula nunca
travar por causa de internet. Uma chamada bem-sucedida sempre atualiza
esse cache.
"""

import json
from pathlib import Path

import duckdb
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "warehouse" / "workshop.duckdb"
CACHE_PATH = ROOT / "data" / "cache" / "weather_snapshot.json"

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

# Janela de datas igual à do CSV de vendas (histórico + incremental), para
# que toda venda tenha um dia de clima correspondente.
START_DATE = "2026-06-01"
END_DATE = "2026-09-01"

# Fallback de coordenadas: usado se a chamada de geocoding falhar.
COORDENADAS_FALLBACK = {
    "Sao Paulo": (-23.5505, -46.6333),
    "Rio de Janeiro": (-22.9068, -43.1729),
    "Curitiba": (-25.4284, -49.2733),
    "Fortaleza": (-3.7172, -38.5433),
    "Porto Alegre": (-30.0346, -51.2177),
}

REQUEST_TIMEOUT = 10


def geocodificar(cidade):
    try:
        resp = requests.get(
            GEOCODING_URL,
            params={"name": cidade, "count": 1, "language": "pt", "format": "json"},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        resultados = resp.json().get("results")
        if resultados:
            return resultados[0]["latitude"], resultados[0]["longitude"]
    except requests.RequestException as e:
        print(f"[extract_weather] geocoding falhou para {cidade} ({e}); usando fallback")
    return COORDENADAS_FALLBACK[cidade]


def buscar_clima(cidade, lat, lon):
    resp = requests.get(
        ARCHIVE_URL,
        params={
            "latitude": lat,
            "longitude": lon,
            "start_date": START_DATE,
            "end_date": END_DATE,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
            "timezone": "America/Sao_Paulo",
        },
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    dados = resp.json()
    daily = dados["daily"]
    return pd.DataFrame({
        "cidade": cidade,
        "data": daily["time"],
        "temp_max_c": daily["temperature_2m_max"],
        "temp_min_c": daily["temperature_2m_min"],
        "precipitacao_mm": daily["precipitation_sum"],
    })


def buscar_clima_todas_cidades():
    frames = []
    for cidade in COORDENADAS_FALLBACK:
        lat, lon = geocodificar(cidade)
        frames.append(buscar_clima(cidade, lat, lon))
        print(f"[extract_weather] clima obtido via API para {cidade}")
    return pd.concat(frames, ignore_index=True)


def salvar_cache(df):
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_json(CACHE_PATH, orient="records", date_format=None)
    print(f"[extract_weather] cache atualizado -> {CACHE_PATH}")


def carregar_cache():
    if not CACHE_PATH.exists():
        raise FileNotFoundError(
            f"Sem conexão com a API e sem cache em {CACHE_PATH}. "
            "Rode este script pelo menos uma vez com internet antes do evento."
        )
    print(f"[extract_weather] API indisponível — usando cache local {CACHE_PATH}")
    return pd.read_json(CACHE_PATH, orient="records")


def obter_dados_clima():
    try:
        df = buscar_clima_todas_cidades()
        salvar_cache(df)
        return df
    except requests.RequestException as e:
        print(f"[extract_weather] falha de rede ({e})")
        return carregar_cache()


def main():
    df = obter_dados_clima()

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH))
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    con.register("_tmp_clima", df)
    con.execute("CREATE OR REPLACE TABLE raw.clima AS SELECT * FROM _tmp_clima")
    con.unregister("_tmp_clima")
    con.close()
    print(f"[extract_weather] {len(df)} linhas -> raw.clima")


if __name__ == "__main__":
    main()

import logging
import os
import random
import sys
import time
from pathlib import Path


## Para que el codigo funcione ejecutar en la consola "copy .env.example .env" y luego python extraer_datos.py




import pandas as pd
import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
REINTENTABLES = {429, 500, 502, 503, 504}

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def cargar_configuracion():
    """Lee la configuración desde el archivo .env (no hay valores fijos en el código)."""
    load_dotenv(BASE_DIR / ".env")
    base_url = os.getenv("API_BASE_URL")
    if not base_url:
        raise ValueError("Falta API_BASE_URL. Copiá .env.example a .env y completalo.")
    try:
        limite = int(os.getenv("POKEMON_LIMIT", "20"))
        max_reintentos = int(os.getenv("MAX_RETRIES", "5"))
    except ValueError:
        raise ValueError("POKEMON_LIMIT y MAX_RETRIES deben ser números enteros.")
    # Si hubiera una API key, se leería igual: os.getenv("API_KEY")
    return {
        "base_url": base_url.rstrip("/"),
        "limite": limite,
        "max_reintentos": max_reintentos,
        "salida": BASE_DIR / os.getenv("OUTPUT_FILE", "data_extracted.csv"),
    }


def esperar(intento, maximo=60):
    """Backoff exponencial con un poco de azar (jitter)."""
    segundos = min(2 ** intento, maximo) + random.uniform(0, 0.5)
    logging.info(f"Reintentando en {segundos:.1f} segundos...")
    time.sleep(segundos)


def get_con_reintentos(url, params=None, max_intentos=5):
    """GET con timeout, reintentos para errores temporales y corte inmediato en errores del cliente."""
    for intento in range(max_intentos):
        try:
            resp = requests.get(url, params=params, timeout=10)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            logging.warning(f"Fallo de red ({e.__class__.__name__}) en intento {intento + 1}/{max_intentos}")
        else:
            if resp.status_code == 200:
                return resp
            if resp.status_code not in REINTENTABLES:
                # 404 y demás 4xx: reintentar no sirve
                raise RuntimeError(f"Error {resp.status_code} (no recuperable) al pedir {url}")
            logging.warning(f"Error {resp.status_code} en intento {intento + 1}/{max_intentos}")
            if resp.status_code == 429 and "Retry-After" in resp.headers:
                time.sleep(float(resp.headers["Retry-After"]))
                continue
        if intento < max_intentos - 1:
            esperar(intento)
    raise RuntimeError(f"La API no respondió correctamente tras {max_intentos} intentos: {url}")


def extraer(config):
    """Pide el listado y luego el detalle de cada pokémon. Devuelve una lista de diccionarios (JSON)."""
    listado = get_con_reintentos(
        f"{config['base_url']}/pokemon",
        params={"limit": config["limite"]},
        max_intentos=config["max_reintentos"],
    ).json()

    detalles = []
    for i, item in enumerate(listado["results"], start=1):
        logging.info(f"({i}/{len(listado['results'])}) {item['name']}")
        resp = get_con_reintentos(item["url"], max_intentos=config["max_reintentos"])
        detalles.append(resp.json())
        time.sleep(0.1)  # pausa corta para ser amable con la API pública
    return detalles


def transformar(detalles):
    """Aplana el JSON anidado y se queda solo con los campos útiles."""
    filas = []
    for p in detalles:
        filas.append({
            "id": p["id"],
            "nombre": p["name"],
            "altura_m": p["height"] / 10,   # la API da decímetros
            "peso_kg": p["weight"] / 10,    # la API da hectogramos
            "experiencia_base": p.get("base_experience"),
            "tipos": ", ".join(t["type"]["name"] for t in p["types"]),
            "habilidades": ", ".join(a["ability"]["name"] for a in p["abilities"]),
        })
    df = pd.DataFrame(filas)
    if df.empty:
        raise ValueError("La API no devolvió datos para transformar.")
    return df


def main():
    try:
        config = cargar_configuracion()
        detalles = extraer(config)
        df = transformar(detalles)
        df.to_csv(config["salida"], index=False, encoding="utf-8")
    except (ValueError, RuntimeError) as e:
        logging.error(e)
        return 1
    except (KeyError, TypeError) as e:
        logging.error(f"La respuesta de la API no tiene la estructura esperada: {e!r}")
        return 1
    logging.info(f"Listo: {len(df)} filas guardadas en {config['salida'].name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
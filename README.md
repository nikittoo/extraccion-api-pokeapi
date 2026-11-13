# Extracción y almacenamiento seguro de datos vía API (PokeAPI)

Script en Python que consume una API pública (**[PokeAPI](https://pokeapi.co/)**), transforma la respuesta JSON anidada en una tabla limpia y la guarda en un CSV. La configuración vive en un archivo `.env` (no se sube al repositorio) y las peticiones fallidas se manejan sin romper el programa.

## ¿Qué hace?

1. Carga la configuración desde `.env` con `python-dotenv`.
2. Pide el listado de pokémon (`GET /pokemon?limit=N`) y luego el detalle de cada uno.
3. Maneja errores: `timeout`, reintentos con backoff exponencial para errores temporales (429, 5xx, caídas de red) y corte inmediato para errores del cliente (404, etc.), con mensajes claros.
4. Aplana el JSON y se queda solo con los campos útiles.
5. Guarda el resultado en `data_extracted.csv`.

## Estructura del repositorio

```
extraccion-api-pokeapi/
├── extraer_datos.py      # script principal
├── requirements.txt      # dependencias
├── .env.example          # plantilla de configuración (se sube)
├── .env                  # tu configuración real (NO se sube, está en .gitignore)
├── .gitignore
├── data_extracted.csv    # salida generada por el script
└── README.md
```

## Instalación

Requiere Python 3.10 o superior.

```bash
# 1. Clonar el repositorio
git clone https://github.com/nikittoo/extraccion-api-pokeapi.git
cd extraccion-api-pokeapi

# 2. Crear y activar un entorno virtual
python -m venv .venv
.venv\Scripts\activate          # Windows (PowerShell)
# source .venv/bin/activate     # macOS / Linux

# 3. Instalar dependencias
python -m pip install -r requirements.txt
```

## Configuración (variables de entorno)

Copiá la plantilla y, si querés, ajustá los valores:

```bash
copy .env.example .env          # Windows
# cp .env.example .env          # macOS / Linux
```

| Variable | Descripción | Valor por defecto |
|---|---|---|
| `API_BASE_URL` | URL base de la API | `https://pokeapi.co/api/v2` |
| `POKEMON_LIMIT` | Cantidad de pokémon a extraer | `20` |
| `MAX_RETRIES` | Intentos máximos por petición | `5` |
| `OUTPUT_FILE` | Nombre del archivo de salida | `data_extracted.csv` |

PokeAPI es pública y no requiere clave, por eso el `.env` guarda configuración y no secretos. Si se usara una API con credenciales, la clave se agregaría ahí (por ejemplo `API_KEY=...`) y el script la leería con `os.getenv`, sin escribirla nunca en el código.

## Ejecución

```bash
python extraer_datos.py
```

Salida esperada en consola (ejemplo):

```
INFO: (1/20) bulbasaur
...
INFO: Listo: 20 filas guardadas en data_extracted.csv
```

## Datos generados

`data_extracted.csv` tiene una fila por pokémon:

| Columna | Descripción |
|---|---|
| `id` | Identificador del pokémon |
| `nombre` | Nombre |
| `altura_m` | Altura en metros (la API la entrega en decímetros) |
| `peso_kg` | Peso en kilogramos (la API lo entrega en hectogramos) |
| `experiencia_base` | Experiencia base otorgada |
| `tipos` | Tipos separados por coma |
| `habilidades` | Habilidades separadas por coma |

## Manejo de errores

| Situación | Comportamiento |
|---|---|
| Falla de red o `timeout` | Reintenta con espera creciente; si se agotan los intentos, muestra un error claro y termina |
| Error `429` o `5xx` | Reintenta con backoff (respeta `Retry-After` si viene) |
| Error `404` u otro `4xx` | No reintenta: informa la URL que falló y termina |
| Falta configuración o valor inválido en `.env` | Avisa qué variable corregir |
| Estructura de respuesta inesperada | Informa el error en lugar de romperse con un traceback |

El script termina con código de salida `1` si hubo un error y `0` si todo salió bien.

## Seguridad

- No hay claves ni URLs sensibles escritas en el código.
- `.env` está en `.gitignore`, así que nunca se sube; solo se versiona `.env.example`.
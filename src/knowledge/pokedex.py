"""Carga el conocimiento Pokemon (tipos, movimientos, mapa) desde los JSON de datos."""

import json
from pathlib import Path

_DATA_DIR = Path(__file__).parent

with open(_DATA_DIR / "pokedex_data.json", encoding="utf-8") as f:
    _pokedex = json.load(f)

TYPE_CHART: dict[str, dict[str, float]] = _pokedex["type_chart"]
ALL_TYPES: list[str] = _pokedex["all_types"]
POKEMON_NAMES: list[str] = _pokedex["pokemon_names"]
MOVES_DATA: dict[str, dict[str, object]] = _pokedex["moves_data"]

with open(_DATA_DIR / "static_map_index.json", encoding="utf-8") as f:
    STATIC_MAP_INDEX: dict = json.load(f)

with open(_DATA_DIR / "moves_es_en.json", encoding="utf-8") as f:
    _moves_es_en = json.load(f)
    _moves_es_en.pop("_nota", None)
MOVES_ES_EN: dict[str, str] = _moves_es_en

with open(_DATA_DIR / "pokemon_tipos.json", encoding="utf-8") as f:
    _pokemon_tipos = json.load(f)
    _pokemon_tipos.pop("_nota", None)
POKEMON_TIPOS: dict[str, list[str]] = _pokemon_tipos


def _normalizar(texto: str) -> str:
    """Quita acentos y pasa a minusculas, para comparar nombres de forma tolerante
    a como los normalice el OCR (que a veces se come tildes o cambia mayusculas)."""
    equivalencias = str.maketrans("áéíóúñ", "aeioun")
    return texto.lower().translate(equivalencias).strip()


_MOVES_ES_EN_NORMALIZADO = {_normalizar(k): v for k, v in MOVES_ES_EN.items()}


def traducir_movimiento(nombre_es: str) -> str | None:
    """Traduce un nombre de movimiento en español (tal como lo lee el OCR del
    juego) a la clave en ingles que usa MOVES_DATA. None si no hay traduccion."""
    return _MOVES_ES_EN_NORMALIZADO.get(_normalizar(nombre_es))


def tipos_de(nombre_pokemon: str) -> list[str]:
    """Tipos conocidos de un Pokemon por nombre. Lista vacia si no esta en POKEMON_TIPOS."""
    return POKEMON_TIPOS.get(nombre_pokemon, [])


def calcular_efectividad(tipo_ataque: str, tipos_defensor: list[str]) -> float:
    """Multiplicador de daño de un tipo de ataque contra uno o dos tipos defensores."""
    multiplicador = 1.0
    tabla = TYPE_CHART.get(tipo_ataque, {})
    for tipo_def in tipos_defensor:
        multiplicador *= tabla.get(tipo_def, 1.0)
    return multiplicador


def _buscar_movimiento(movimiento: str) -> dict | None:
    """Busca un movimiento en MOVES_DATA probando: tal cual, con espacios->guiones,
    y traducido desde español (en ese orden)."""
    for clave in (movimiento, movimiento.replace(" ", "-"), traducir_movimiento(movimiento)):
        if clave and clave in MOVES_DATA:
            return MOVES_DATA[clave]
    return None


def describir_efectividad(movimiento: str, tipos_enemigo: list[str]) -> str:
    """Genera una frase legible sobre la efectividad de un movimiento, para pasarle a Jev como contexto."""
    data = _buscar_movimiento(movimiento)
    if not data:
        return f"{movimiento}: datos de tipo desconocidos"

    tipo_mov = data.get("type", "")
    poder = data.get("power", 0)
    efectividad = calcular_efectividad(tipo_mov, tipos_enemigo) if tipos_enemigo else 1.0

    if efectividad >= 2.0:
        etiqueta = "muy efectivo (x2 o mas)"
    elif efectividad <= 0.0:
        etiqueta = "sin efecto"
    elif efectividad < 1.0:
        etiqueta = "poco efectivo"
    else:
        etiqueta = "efectividad normal"

    return f"{movimiento} (tipo {tipo_mov}, poder {poder}): {etiqueta}"

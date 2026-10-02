"""Cliente de decision de combate via Jev (typesafe-sdk).

Dos pasos separados (Q18 del plan): primero el menu principal (Luchar/Mochila/
Pokemon/Huir), despues -si corresponde luchar- el movimiento concreto. Cada
pregunta es mas chica y barata, y permite ver en que paso fallo si algo sale mal.
"""

import logging

from typesafe_sdk import Choice, TypeSafeClient

from src.decision.state_builder import EstadoCombate, construir_estado_texto

logger = logging.getLogger(__name__)

_client: TypeSafeClient | None = None


def _get_client() -> TypeSafeClient:
    global _client
    if _client is None:
        _client = TypeSafeClient()
    return _client


def decidir_menu(estado: EstadoCombate) -> str:
    """Devuelve una de: 'luchar', 'mochila', 'pokemon', 'huir'."""
    texto_estado = construir_estado_texto(estado)
    preguntas = {
        "menu": Choice(
            instructions=(
                f"{texto_estado}\n\n"
                "¿Que deberiamos hacer este turno? Por defecto, luchar es la opcion "
                "normal salvo que haya una razon clara para huir o cambiar de Pokemon."
            ),
            criteria={"luchar": None, "mochila": None, "pokemon": None, "huir": None},
        )
    }
    resultado = _get_client().system_one(texto_estado, preguntas)
    decision = resultado.choices["menu"].choice
    logger.info(f"[Jev] menu -> {decision}")
    return decision


def decidir_movimiento(estado: EstadoCombate) -> str:
    """Devuelve el nombre exacto (tal cual vino del OCR) del movimiento elegido."""
    texto_estado = construir_estado_texto(estado)
    criteria = {m: None for m in estado.movimientos}
    preguntas = {
        "movimiento": Choice(
            instructions=(
                f"{texto_estado}\n\n"
                "Elige el mejor movimiento para este turno, considerando tipo y poder."
            ),
            criteria=criteria,
        )
    }
    resultado = _get_client().system_one(texto_estado, preguntas)
    decision = resultado.choices["movimiento"].choice
    logger.info(f"[Jev] movimiento -> {decision}")
    return decision


def decidir_item(estado: EstadoCombate, items: list[str]) -> str:
    """Devuelve el nombre exacto del item elegido en la mochila."""
    texto_estado = construir_estado_texto(estado)
    criteria = {i: None for i in items}
    preguntas = {
        "item": Choice(
            instructions=(
                f"{texto_estado}\n\n"
                "Elige el mejor objeto de la mochila para usar ahora mismo."
            ),
            criteria=criteria,
        )
    }
    resultado = _get_client().system_one(texto_estado, preguntas)
    decision = resultado.choices["item"].choice
    logger.info(f"[Jev] item -> {decision}")
    return decision


def decidir_cambio_pokemon(estado: EstadoCombate, equipo: list[str]) -> str:
    """Devuelve el nombre exacto del Pokemon del equipo al que cambiar."""
    texto_estado = construir_estado_texto(estado)
    criteria = {p: None for p in equipo}
    preguntas = {
        "cambio": Choice(
            instructions=(
                f"{texto_estado}\n\n"
                "Elige a que Pokemon del equipo cambiar, considerando ventaja de tipo "
                "y HP disponible."
            ),
            criteria=criteria,
        )
    }
    resultado = _get_client().system_one(texto_estado, preguntas)
    decision = resultado.choices["cambio"].choice
    logger.info(f"[Jev] cambio de pokemon -> {decision}")
    return decision

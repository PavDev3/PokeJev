"""Decision de combate en Showdown via Jev. Mismo patron que src/decision/jev_client.py
(Choice de typesafe-sdk), pero el estado viene del protocolo de Showdown en vez
de OCR -- texto limpio y fiable, sin necesidad de visión."""

import logging

from typesafe_sdk import Choice, TypeSafeClient

from showdown.estado import EstadoBatalla

logger = logging.getLogger(__name__)

_client: TypeSafeClient | None = None


def _get_client() -> TypeSafeClient:
    global _client
    if _client is None:
        _client = TypeSafeClient()
    return _client


def _texto_estado(estado: EstadoBatalla) -> str:
    lineas = []
    activo = estado.pokemon_activo
    if activo:
        lineas.append(f"Nuestro Pokemon activo: {activo.nombre} (HP: {activo.condicion})")

    if estado.movimientos:
        lineas.append("Movimientos disponibles:")
        for m in estado.movimientos:
            estado_mov = "deshabilitado" if m.deshabilitado or m.pp == 0 else f"PP: {m.pp}"
            lineas.append(f"- {m.nombre} ({estado_mov})")

    banca = [p for p in estado.equipo if not p.activo]
    if banca:
        lineas.append("Resto del equipo:")
        for p in banca:
            disponible = "disponible" if p.puede_cambiar else "debilitado/no disponible"
            lineas.append(f"- {p.nombre} (HP: {p.condicion}, {disponible})")

    return "\n".join(lineas)


def decidir_accion(estado: EstadoBatalla) -> tuple[str, int]:
    """Devuelve (tipo, indice): tipo es 'move' o 'switch', indice es 1-based
    tal como lo espera el comando /choose de Showdown."""
    texto = _texto_estado(estado)

    if estado.debe_cambiar:
        return _decidir_switch(estado, texto)

    opciones_movimiento = {
        m.nombre: None for m in estado.movimientos if not m.deshabilitado and m.pp > 0
    }
    opciones_switch = {p.nombre: None for p in estado.equipo if p.puede_cambiar}

    if not opciones_movimiento:
        # Sin movimientos utilizables (todos deshabilitados/sin PP) -- forzado a cambiar
        return _decidir_switch(estado, texto)

    criteria = {**opciones_movimiento, **{f"cambiar a {n}": None for n in opciones_switch}}
    preguntas = {
        "accion": Choice(
            instructions=(
                f"{texto}\n\n"
                "Elige la mejor accion para este turno: un movimiento para atacar, "
                "o cambiar de Pokemon si hay una razon clara (desventaja de tipo, HP critico)."
            ),
            criteria=criteria,
        )
    }
    resultado = _get_client().system_one(texto, preguntas)
    decision = resultado.choices["accion"].choice
    logger.info(f"[Jev] accion -> {decision}")

    if decision.startswith("cambiar a "):
        nombre = decision[len("cambiar a ") :]
        indice = next(i for i, p in enumerate(estado.equipo, start=1) if p.nombre == nombre)
        return "switch", indice

    indice = next(i for i, m in enumerate(estado.movimientos, start=1) if m.nombre == decision)
    return "move", indice


def _decidir_switch(estado: EstadoBatalla, texto: str) -> tuple[str, int]:
    opciones = {p.nombre: None for p in estado.equipo if p.puede_cambiar}
    preguntas = {
        "switch": Choice(
            instructions=f"{texto}\n\nElige a que Pokemon cambiar.",
            criteria=opciones,
        )
    }
    resultado = _get_client().system_one(texto, preguntas)
    decision = resultado.choices["switch"].choice
    logger.info(f"[Jev] switch -> {decision}")
    indice = next(i for i, p in enumerate(estado.equipo, start=1) if p.nombre == decision)
    return "switch", indice

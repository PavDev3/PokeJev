"""Construye la descripcion en texto del estado de combate para pasarle a Jev.

Usa src.knowledge.pokedex para traducir movimientos (el juego los muestra en
espanol, MOVES_DATA esta en ingles) y, cuando se conocen los tipos del enemigo
(POKEMON_TIPOS), calcular la efectividad real en vez de solo informar tipo/poder.
"""

from dataclasses import dataclass

from src.knowledge.pokedex import describir_efectividad, tipos_de


@dataclass
class EstadoCombate:
    enemigo_nombre: str
    enemigo_hp_pct: int | None
    jugador_nombre: str
    jugador_hp_actual: int | None
    jugador_hp_maximo: int | None
    movimientos: list[str]  # nombres tal cual los lee el OCR


def construir_estado_texto(estado: EstadoCombate) -> str:
    jugador_hp = (
        f"{estado.jugador_hp_actual}/{estado.jugador_hp_maximo}"
        if estado.jugador_hp_actual is not None
        else "desconocido"
    )
    enemigo_hp = f"{estado.enemigo_hp_pct}%" if estado.enemigo_hp_pct is not None else "desconocido"

    lineas = [
        f"Nuestro Pokemon: {estado.jugador_nombre} (HP: {jugador_hp})",
        f"Pokemon enemigo: {estado.enemigo_nombre} (HP: {enemigo_hp})",
    ]

    tipos_enemigo = tipos_de(estado.enemigo_nombre)
    if tipos_enemigo:
        lineas.append(f"Tipos del enemigo: {', '.join(tipos_enemigo)}")

    if estado.movimientos:
        lineas.append("Movimientos disponibles:")
        lineas.extend(f"- {describir_efectividad(m, tipos_enemigo)}" for m in estado.movimientos)

    return "\n".join(lineas)

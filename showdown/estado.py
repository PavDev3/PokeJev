"""Parsea el JSON de |request| de Showdown a un estado simple para decidir."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class OpcionMovimiento:
    nombre: str
    id_movimiento: str
    pp: int
    deshabilitado: bool


@dataclass
class PokemonEquipo:
    nombre: str
    condicion: str  # ej. "100/100" o "0 fnt"
    activo: bool
    puede_cambiar: bool


@dataclass
class EstadoBatalla:
    movimientos: list[OpcionMovimiento]
    equipo: list[PokemonEquipo]
    debe_cambiar: bool

    @property
    def pokemon_activo(self) -> PokemonEquipo | None:
        return next((p for p in self.equipo if p.activo), None)


def parsear_estado(request_json: dict) -> EstadoBatalla:
    debe_cambiar = bool(request_json.get("forceSwitch"))

    movimientos = []
    if not debe_cambiar and request_json.get("active"):
        for mov in request_json["active"][0].get("moves", []):
            movimientos.append(
                OpcionMovimiento(
                    nombre=mov["move"],
                    id_movimiento=mov["id"],
                    pp=mov.get("pp", 0),
                    deshabilitado=mov.get("disabled", False),
                )
            )

    equipo = []
    for p in request_json.get("side", {}).get("pokemon", []):
        condicion = p.get("condition", "")
        activo = p.get("active", False)
        equipo.append(
            PokemonEquipo(
                nombre=p["details"].split(",")[0],
                condicion=condicion,
                activo=activo,
                puede_cambiar=not activo and "fnt" not in condicion,
            )
        )

    return EstadoBatalla(movimientos=movimientos, equipo=equipo, debe_cambiar=debe_cambiar)

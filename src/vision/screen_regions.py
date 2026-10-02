"""Carga la calibracion (anclas y regiones) desde calibration/anchors.json."""

import json
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent.parent
_CALIBRATION_DIR = _PROJECT_ROOT / "calibration"

with open(_CALIBRATION_DIR / "anchors.json", encoding="utf-8") as f:
    _anchors = json.load(f)

RESOLUCION_REFERENCIA: tuple[int, int] = tuple(_anchors["resolucion_referencia"])
REGIONES: dict[str, tuple[int, int, int, int]] = {
    nombre: tuple(box) for nombre, box in _anchors["regiones"].items()
}
BOTONES_COMBATE: dict[str, tuple[int, int, int, int]] = {
    nombre: tuple(box) for nombre, box in _anchors["botones_combate"].items()
}
BOTONES_MOVIMIENTOS: dict[str, tuple[int, int, int, int]] = {
    nombre: tuple(box) for nombre, box in _anchors["botones_movimientos"].items()
}

ANCLA_COMBATE = _CALIBRATION_DIR / "templates" / "anchor_combate_luchar.png"
ANCLA_COMBATE_MOVIMIENTOS = _CALIBRATION_DIR / "templates" / "anchor_combate_movimientos.png"
ANCLA_DIALOGO = _CALIBRATION_DIR / "templates" / "anchor_dialogo.png"

"""Clasifica el tipo de pantalla actual por template matching.

Estados:
- 'combate_menu': menu principal de combate (Luchar/Mochila/Pokemon/Huir)
- 'combate_movimientos': pantalla de seleccion de movimiento
- 'dialogo': cuadro de dialogo con indicador de continuar
- 'exploracion': cualquier otra cosa (movimiento libre, Fase 4 sin logica propia aun)
"""

import cv2
import numpy as np

from src.vision.screen_regions import ANCLA_COMBATE, ANCLA_COMBATE_MOVIMIENTOS, ANCLA_DIALOGO

UMBRAL_COINCIDENCIA = 0.80

_plantilla_menu = cv2.imread(str(ANCLA_COMBATE), cv2.IMREAD_COLOR)
_plantilla_movimientos = cv2.imread(str(ANCLA_COMBATE_MOVIMIENTOS), cv2.IMREAD_COLOR)
_plantilla_dialogo = cv2.imread(str(ANCLA_DIALOGO), cv2.IMREAD_COLOR)


def _coincide(captura_bgr: np.ndarray, plantilla: np.ndarray) -> bool:
    resultado = cv2.matchTemplate(captura_bgr, plantilla, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(resultado)
    return max_val >= UMBRAL_COINCIDENCIA


def clasificar_pantalla(captura_bgr: np.ndarray) -> str:
    if _coincide(captura_bgr, _plantilla_menu):
        return "combate_menu"
    if _coincide(captura_bgr, _plantilla_movimientos):
        return "combate_movimientos"
    if _coincide(captura_bgr, _plantilla_dialogo):
        return "dialogo"
    return "exploracion"

"""Deteccion de movimiento/colision por comparacion de fotogramas (sin posicion real).

Sin un modelo de vision que describa la escena, esto es lo mas confiable que podemos
hacer: si la pantalla no cambio (o casi no cambio) tras intentar movernos, es que
chocamos contra algo. Mismo principio que el sistema anti-stuck del proyecto viejo.
"""

import cv2
import numpy as np


def hash_perceptual(captura_bgr: np.ndarray, tamano: int = 24) -> np.ndarray:
    """Hash perceptual simple: reduce la imagen y binariza contra el promedio.
    Tolerante a pequeños cambios de animacion (parpadeos, sprites menores)."""
    gris = cv2.cvtColor(captura_bgr, cv2.COLOR_BGR2GRAY)
    chico = cv2.resize(gris, (tamano, tamano), interpolation=cv2.INTER_AREA)
    promedio = chico.mean()
    return chico > promedio


def distancia_hash(hash_a: np.ndarray, hash_b: np.ndarray) -> int:
    """Numero de bits distintos entre dos hashes (distancia de Hamming)."""
    return int(np.count_nonzero(hash_a != hash_b))


def hubo_movimiento(antes_bgr: np.ndarray, despues_bgr: np.ndarray, umbral: int = 20) -> bool:
    """True si la escena cambio lo suficiente como para asumir que el personaje
    se movio de verdad (no solo una animacion menor de fondo)."""
    h1 = hash_perceptual(antes_bgr)
    h2 = hash_perceptual(despues_bgr)
    return distancia_hash(h1, h2) >= umbral

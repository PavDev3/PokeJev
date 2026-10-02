"""Bucle principal del bot de combate.

Fase 5 del plan: solo combate (exploracion queda para Fase 4, no implementada aun --
si detecta 'exploracion' simplemente espera, para no mandar teclas a ciegas).

Fallback ante fallo de Jev (Q17 del plan): loguear, tomar una accion segura minima
(primera opcion disponible) para no quedar trabado a mitad de turno, y pausar el
bot esperando supervision -- no sigue jugando solo despues de un fallo.
"""

import logging
import time

from src.control.input_handler import avanzar_dialogo, mover, seleccionar_en_grid
from src.vision.motion import hubo_movimiento
from src.decision.jev_client import decidir_menu, decidir_movimiento
from src.decision.state_builder import EstadoCombate
from src.vision.capture import VentanaNoEncontradaError, capturar_juego
from src.vision.classifier import clasificar_pantalla
from src.vision.ocr import (
    extraer_hp_absoluto,
    extraer_nombre,
    extraer_nombre_movimiento,
    extraer_porcentaje_hp,
    leer_texto,
)
from src.vision.screen_regions import BOTONES_MOVIMIENTOS, REGIONES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("logs/pokejev.log", encoding="utf-8"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

_POSICION_GRID_MENU = {"luchar": (0, 0), "mochila": (0, 1), "pokemon": (1, 0), "huir": (1, 1)}
_ORDEN_BOTONES_MOV = ["mov1", "mov2", "mov3", "mov4"]
_POSICION_GRID_MOV = {"mov1": (0, 0), "mov2": (0, 1), "mov3": (1, 0), "mov4": (1, 1)}

PAUSA_ENTRE_CICLOS = 1.0


def _recortar(captura, region_nombre: str):
    x1, y1, x2, y2 = REGIONES[region_nombre]
    return captura[y1:y2, x1:x2]


def _leer_info_combate(captura) -> tuple[str, int | None, str, int | None, int | None]:
    frags_enemigo = leer_texto(_recortar(captura, "enemigo_info"))
    frags_jugador = leer_texto(_recortar(captura, "jugador_info"))

    enemigo_nombre = extraer_nombre(frags_enemigo)
    enemigo_hp_pct = extraer_porcentaje_hp(frags_enemigo)
    jugador_nombre = extraer_nombre(frags_jugador)
    hp_abs = extraer_hp_absoluto(frags_jugador)
    jugador_hp_actual, jugador_hp_maximo = hp_abs if hp_abs else (None, None)

    return enemigo_nombre, enemigo_hp_pct, jugador_nombre, jugador_hp_actual, jugador_hp_maximo


def _leer_movimientos(captura) -> list[str]:
    movimientos = []
    for nombre_boton in _ORDEN_BOTONES_MOV:
        x1, y1, x2, y2 = BOTONES_MOVIMIENTOS[nombre_boton]
        frags = leer_texto(captura[y1:y2, x1:x2])
        nombre_mov = extraer_nombre_movimiento(frags)
        if nombre_mov:
            movimientos.append(nombre_mov)
    return movimientos


def _accion_segura_menu() -> None:
    """Fallback: elegir 'luchar' (primera opcion del menu principal)."""
    logger.warning("[FALLBACK] Accion segura: seleccionando 'luchar' en el menu")
    seleccionar_en_grid(0, 0)


def _accion_segura_movimiento() -> None:
    """Fallback: elegir el primer movimiento disponible."""
    logger.warning("[FALLBACK] Accion segura: seleccionando el primer movimiento")
    seleccionar_en_grid(0, 0)


def ciclo_combate_menu(captura) -> bool:
    """Devuelve True si pudo actuar con normalidad, False si tuvo que usar el fallback."""
    enemigo_nombre, enemigo_hp_pct, jugador_nombre, hp_act, hp_max = _leer_info_combate(captura)
    estado = EstadoCombate(
        enemigo_nombre=enemigo_nombre,
        enemigo_hp_pct=enemigo_hp_pct,
        jugador_nombre=jugador_nombre,
        jugador_hp_actual=hp_act,
        jugador_hp_maximo=hp_max,
        movimientos=[],
    )
    logger.info(f"[ESTADO] {jugador_nombre} ({hp_act}/{hp_max}) vs {enemigo_nombre} ({enemigo_hp_pct}%)")

    try:
        decision = decidir_menu(estado)
        fila, col = _POSICION_GRID_MENU.get(decision, (0, 0))
        seleccionar_en_grid(fila, col)
        return True
    except Exception:
        logger.exception("[ERROR] Fallo al decidir el menu de combate")
        _accion_segura_menu()
        return False


def ciclo_combate_movimientos(captura) -> bool:
    enemigo_nombre, enemigo_hp_pct, jugador_nombre, hp_act, hp_max = _leer_info_combate(captura)
    movimientos = _leer_movimientos(captura)

    if not movimientos:
        logger.warning("[FALLBACK] No se pudo leer ningun movimiento, cancelando para reintentar")
        from src.control.input_handler import cancelar

        cancelar()
        return False

    estado = EstadoCombate(
        enemigo_nombre=enemigo_nombre,
        enemigo_hp_pct=enemigo_hp_pct,
        jugador_nombre=jugador_nombre,
        jugador_hp_actual=hp_act,
        jugador_hp_maximo=hp_max,
        movimientos=movimientos,
    )
    logger.info(f"[ESTADO] Movimientos disponibles: {movimientos}")

    try:
        decision = decidir_movimiento(estado)
        indice = movimientos.index(decision) if decision in movimientos else 0
        fila, col = _POSICION_GRID_MOV[_ORDEN_BOTONES_MOV[indice]]
        seleccionar_en_grid(fila, col)
        return True
    except Exception:
        logger.exception("[ERROR] Fallo al decidir el movimiento de combate")
        _accion_segura_movimiento()
        return False


_ORDEN_ROTACION = ["arriba", "derecha", "abajo", "izquierda"]


def ciclo_exploracion(captura_antes, direccion_actual: str) -> str:
    """Exploracion 'a ciegas': sin posicion real, solo detecta colision por
    fotogramas. Si la direccion actual funciona, sigue derecho; si choca,
    rota a la siguiente direccion de la lista."""
    mover(direccion_actual)
    time.sleep(0.2)
    captura_despues = capturar_juego()

    if hubo_movimiento(captura_antes, captura_despues):
        logger.info(f"[EXPLORACION] Avanzando hacia '{direccion_actual}'")
        return direccion_actual

    siguiente = _ORDEN_ROTACION[(_ORDEN_ROTACION.index(direccion_actual) + 1) % 4]
    logger.info(f"[EXPLORACION] Bloqueado hacia '{direccion_actual}', rotando a '{siguiente}'")
    return siguiente


def ejecutar_bot() -> None:
    logger.info("=== PokeJev iniciado ===")
    direccion_exploracion = "abajo"

    while True:
        try:
            captura = capturar_juego()
        except VentanaNoEncontradaError as e:
            logger.error(f"[ERROR] {e}")
            logger.error("[PAUSA] Ventana del juego no disponible. Pausando bot.")
            return

        estado_pantalla = clasificar_pantalla(captura)

        if estado_pantalla == "combate_menu":
            ok = ciclo_combate_menu(captura)
        elif estado_pantalla == "combate_movimientos":
            ok = ciclo_combate_movimientos(captura)
        elif estado_pantalla == "dialogo":
            logger.info("[DIALOGO] Avanzando texto")
            avanzar_dialogo()
            ok = True
        else:
            direccion_exploracion = ciclo_exploracion(captura, direccion_exploracion)
            ok = True

        if not ok:
            logger.error("[PAUSA] Fallo de decision tras usar la accion de emergencia. Pausando bot para supervision.")
            return

        time.sleep(PAUSA_ENTRE_CICLOS)


if __name__ == "__main__":
    ejecutar_bot()

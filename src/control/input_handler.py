"""Simula pulsaciones de teclado para controlar el juego.

Controles confirmados: Intro = confirmar, Escape = cancelar, flechas = mover cursor.
"""

import time

from pynput.keyboard import Controller, Key

from src.vision.capture import enfocar_ventana

_teclado = Controller()

_FLECHAS = {
    "arriba": Key.up,
    "abajo": Key.down,
    "izquierda": Key.left,
    "derecha": Key.right,
}


def _pulsar(tecla, duracion: float = 0.08) -> None:
    enfocar_ventana()
    _teclado.press(tecla)
    time.sleep(duracion)
    _teclado.release(tecla)
    time.sleep(0.05)  # pequeno respiro para que el juego registre la pulsacion


def confirmar() -> None:
    _pulsar(Key.enter)


def cancelar() -> None:
    _pulsar(Key.esc)


def mover(direccion: str) -> None:
    """Pulsacion larga (0.5s) -- una pulsacion corta solo gira al personaje sin
    moverlo si no estaba ya mirando hacia esa direccion, confirmado empiricamente."""
    if direccion not in _FLECHAS:
        raise ValueError(f"Direccion invalida: {direccion!r} (validas: {list(_FLECHAS)})")
    _pulsar(_FLECHAS[direccion], duracion=0.5)


def avanzar_dialogo() -> None:
    confirmar()


def seleccionar_en_grid(fila: int, columna: int) -> None:
    """Navega un menu en cuadricula 2x2 y confirma. No sabemos en que opcion esta
    el cursor al entrar, asi que primero lo resetea al origen (arriba-izquierda)
    con el maximo de pasos posibles en una grilla 2x2, y de ahi navega al objetivo."""
    mover("arriba")
    mover("izquierda")
    mover("arriba")
    mover("izquierda")

    for _ in range(fila):
        mover("abajo")
    for _ in range(columna):
        mover("derecha")

    confirmar()

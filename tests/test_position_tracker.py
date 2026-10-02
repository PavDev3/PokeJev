"""Tests del tracking de posicion con fuente de memoria y movimiento simulados
(sin pymem real, sin juego abierto)."""

import numpy as np

from src.control.memory_reader import Snapshot
from src.control.position_tracker import UMBRAL_RECALIBRACION, RastreadorPosicion

BASE = 0x1000
N_DIRECCIONES = 12
ADDR_X = BASE + 4 * 3
ADDR_Y = BASE + 4 * 7


class FuenteMemoriaFalsa:
    """Simula la memoria heap del proceso: N direcciones consecutivas de 4
    bytes, donde ADDR_X/ADDR_Y son las que de verdad siguen al jugador."""

    def __init__(self):
        self.valores = {BASE + i * 4: 100 + i for i in range(N_DIRECCIONES)}

    def tomar_snapshot(self) -> Snapshot:
        direcciones = sorted(self.valores)
        arr = np.array([self.valores[d] for d in direcciones], dtype=np.int32)
        return Snapshot(regiones={direcciones[0]: arr})

    def leer_entero(self, direccion: int) -> int:
        return self.valores[direccion]


class MovedorEstable:
    """Mundo 'bien portado': ADDR_X/ADDR_Y siguen el protocolo Fixnum sin fallos."""

    def __init__(self, fuente: FuenteMemoriaFalsa):
        self.fuente = fuente

    def __call__(self, direccion: str) -> None:
        deltas_x = {"derecha": 2, "izquierda": -2}
        deltas_y = {"abajo": 2, "arriba": -2}
        if direccion in deltas_x:
            self.fuente.valores[ADDR_X] += deltas_x[direccion]
        if direccion in deltas_y:
            self.fuente.valores[ADDR_Y] += deltas_y[direccion]


def test_recalibracion_encuentra_las_direcciones_correctas():
    fuente = FuenteMemoriaFalsa()
    movedor = MovedorEstable(fuente)
    tracker = RastreadorPosicion(fuente)

    tracker.mantenimiento(movedor)

    assert tracker.confianza[0] >= UMBRAL_RECALIBRACION
    assert tracker.confianza[1] >= UMBRAL_RECALIBRACION
    assert tracker.leer_posicion() is not None


def test_posicion_se_actualiza_tras_movimientos_confirmados():
    fuente = FuenteMemoriaFalsa()
    movedor = MovedorEstable(fuente)
    tracker = RastreadorPosicion(fuente)
    tracker.mantenimiento(movedor)

    x0, y0 = tracker.leer_posicion()

    tracker.iniciar_paso()
    movedor("derecha")
    tracker.confirmar_paso("derecha")

    x1, y1 = tracker.leer_posicion()
    assert x1 == x0 + 1  # +2 crudo (Fixnum) == +1 en la coordenada decodificada
    assert y1 == y0


def test_confianza_sube_con_movimientos_consistentes():
    fuente = FuenteMemoriaFalsa()
    movedor = MovedorEstable(fuente)
    tracker = RastreadorPosicion(fuente)
    tracker.mantenimiento(movedor)

    # Forzamos un valor intermedio (en vez del 1.0 tras calibrar) para
    # comprobar que un movimiento consistente efectivamente la sube.
    tracker._ejes["x"].confianza = 0.5

    tracker.iniciar_paso()
    movedor("derecha")
    tracker.confirmar_paso("derecha")

    assert tracker.confianza[0] > 0.5


def test_confianza_baja_y_posicion_deja_de_reportarse_tras_invalidacion_gc():
    fuente = FuenteMemoriaFalsa()
    movedor = MovedorEstable(fuente)
    tracker = RastreadorPosicion(fuente)
    tracker.mantenimiento(movedor)
    assert tracker.leer_posicion() is not None

    # Simular que el GC de Ruby reubico el objeto: la direccion calibrada ya
    # no responde a los movimientos (se queda fija), tal como vimos en vivo
    # con el juego real (valores que se congelan poco despues de calibrar).
    direccion_invalida = tracker._ejes["x"].direccion_memoria
    fuente.valores[direccion_invalida] = 777

    def movedor_sin_efecto_en_x(direccion: str) -> None:
        pass  # el movimiento ya no afecta la direccion que creiamos X

    for _ in range(5):
        tracker.iniciar_paso()
        movedor_sin_efecto_en_x("derecha")
        tracker.confirmar_paso("derecha")

    assert tracker.confianza[0] < UMBRAL_RECALIBRACION
    assert tracker.leer_posicion() is None


def test_recalibracion_automatica_recupera_una_direccion_tras_invalidacion():
    fuente = FuenteMemoriaFalsa()
    movedor = MovedorEstable(fuente)
    tracker = RastreadorPosicion(fuente)
    tracker.mantenimiento(movedor)

    tracker._ejes["x"].confianza = 0.0
    tracker._ejes["x"].ultimo_intento_recalibracion = -999.0  # saltar el cooldown

    tracker.mantenimiento(movedor)

    assert tracker.confianza[0] >= UMBRAL_RECALIBRACION
    assert tracker.leer_posicion() is not None


def test_cooldown_evita_recalibrar_en_cada_ciclo():
    fuente = FuenteMemoriaFalsa()
    tracker = RastreadorPosicion(fuente)  # nunca calibrado: ambos ejes en confianza 0.0

    llamadas = []

    def movedor_que_no_arregla_nada(direccion: str) -> None:
        llamadas.append(direccion)  # no toca fuente.valores, nunca calibra bien

    tracker.mantenimiento(movedor_que_no_arregla_nada)
    llamadas_primera_pasada = len(llamadas)
    assert llamadas_primera_pasada > 0  # si intento recalibrar

    tracker.mantenimiento(movedor_que_no_arregla_nada)
    assert len(llamadas) == llamadas_primera_pasada  # cooldown activo, no reintento aun

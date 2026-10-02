"""Tracking de posicion continuo con auto-recalibracion.

Las direcciones de memoria de X/Y encontradas por calibracion (ver
memory_reader.py) dejan de ser validas en segundos porque el recolector de
basura de Ruby reubica los objetos del heap -- confirmado en vivo hoy mismo:
valores que suben al moverse a la izquierda, que no cambian al moverse, o que
se quedan fijos poco despues de calibrar. Este modulo no resuelve ese
problema de fondo (es inherente al motor), pero lo hace manejable: valida
cada movimiento contra el delta esperado, baja la confianza cuando algo no
cuadra, y dispara una recalibracion automatica cuando la confianza cae
demasiado -- en vez de asumir ciegamente que una direccion calibrada una vez
sigue siendo valida para siempre.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Protocol

from src.control.memory_reader import Snapshot, direcciones_con_delta

logger = logging.getLogger(__name__)

MovedorFn = Callable[[str], None]

DELTA_PASO = 2  # un paso de 1 casilla cambia el Fixnum crudo en memoria en +/-2

_EJES: dict[str, dict[str, int]] = {
    "x": {"derecha": DELTA_PASO, "izquierda": -DELTA_PASO},
    "y": {"abajo": DELTA_PASO, "arriba": -DELTA_PASO},
}

UMBRAL_RECALIBRACION = 0.3
INCREMENTO_CONFIANZA = 0.15
DECREMENTO_CONFIANZA = 0.34
COOLDOWN_RECALIBRACION_SEGUNDOS = 5.0


class FuenteMemoria(Protocol):
    """Abstrae el acceso a memoria del proceso para poder testear sin pymem
    real ni un juego abierto. La implementacion de produccion es
    memory_reader.FuenteMemoriaPymem."""

    def tomar_snapshot(self) -> Snapshot: ...

    def leer_entero(self, direccion: int) -> int: ...


@dataclass
class _EstadoEje:
    direccion_memoria: int | None = None
    confianza: float = 0.0
    ultimo_intento_recalibracion: float = field(
        default_factory=lambda: -COOLDOWN_RECALIBRACION_SEGUNDOS
    )


class RastreadorPosicion:
    """Mantiene y valida continuamente las direcciones de memoria de X e Y."""

    def __init__(self, fuente: FuenteMemoria) -> None:
        self._fuente = fuente
        self._ejes: dict[str, _EstadoEje] = {"x": _EstadoEje(), "y": _EstadoEje()}
        self._snapshot_pendiente: dict[str, int | None] | None = None

    # -- lectura --------------------------------------------------------

    def leer_posicion(self) -> tuple[int, int] | None:
        """Lectura pura, sin mover nada ni disparar recalibracion. Devuelve
        None si no hay confianza suficiente en alguno de los dos ejes, en vez
        de un valor que podria ser basura."""
        eje_x, eje_y = self._ejes["x"], self._ejes["y"]
        if (
            eje_x.direccion_memoria is None
            or eje_y.direccion_memoria is None
            or eje_x.confianza < UMBRAL_RECALIBRACION
            or eje_y.confianza < UMBRAL_RECALIBRACION
        ):
            return None

        try:
            x = self._fuente.leer_entero(eje_x.direccion_memoria) // 2
            y = self._fuente.leer_entero(eje_y.direccion_memoria) // 2
        except Exception:
            logger.warning("No se pudo leer la posicion, direccion de memoria invalida")
            return None
        return x, y

    @property
    def confianza(self) -> tuple[float, float]:
        """Confianza actual (x, y), cada una entre 0.0 y 1.0."""
        return self._ejes["x"].confianza, self._ejes["y"].confianza

    # -- validacion continua por movimiento ------------------------------

    def iniciar_paso(self) -> None:
        """Llamar justo antes de ejecutar un movimiento conocido."""
        self._snapshot_pendiente = {
            nombre: (
                None
                if estado.direccion_memoria is None
                else self._leer_seguro(estado.direccion_memoria)
            )
            for nombre, estado in self._ejes.items()
        }

    def confirmar_paso(self, direccion: str) -> None:
        """Llamar justo despues de ejecutar el movimiento de 'direccion'.
        Compara el delta observado en cada eje calibrado contra el esperado
        para esa direccion y ajusta la confianza en consecuencia."""
        if self._snapshot_pendiente is None:
            return  # no se llamo iniciar_paso antes, no hay nada que comparar

        antes = self._snapshot_pendiente
        self._snapshot_pendiente = None

        for nombre_eje, deltas in _EJES.items():
            delta_esperado = deltas.get(direccion)
            estado = self._ejes[nombre_eje]
            valor_antes = antes.get(nombre_eje)

            if delta_esperado is None or estado.direccion_memoria is None or valor_antes is None:
                continue  # esta direccion no afecta a este eje, o aun no esta calibrado

            valor_despues = self._leer_seguro(estado.direccion_memoria)
            if valor_despues is None or valor_despues - valor_antes != delta_esperado:
                if valor_despues is not None:
                    logger.info(
                        f"[{nombre_eje}] delta esperado {delta_esperado}, observado "
                        f"{valor_despues - valor_antes} -- confianza baja"
                    )
                self._penalizar(nombre_eje)
            else:
                self._reforzar(nombre_eje)

    def _leer_seguro(self, direccion: int) -> int | None:
        try:
            return self._fuente.leer_entero(direccion)
        except Exception:
            return None

    def _reforzar(self, nombre_eje: str) -> None:
        estado = self._ejes[nombre_eje]
        estado.confianza = min(1.0, estado.confianza + INCREMENTO_CONFIANZA)

    def _penalizar(self, nombre_eje: str) -> None:
        estado = self._ejes[nombre_eje]
        estado.confianza = max(0.0, estado.confianza - DECREMENTO_CONFIANZA)

    # -- recalibracion automatica -----------------------------------------

    def mantenimiento(self, movedor: MovedorFn) -> None:
        """Llamar periodicamente desde el loop principal (ej. cada ciclo de
        exploracion). Si algun eje perdio confianza, intenta recalibrarlo --
        con cooldown para no reintentar en cada ciclo si acaba de fallar, y
        sin bloquear mas que los pocos movimientos que pide el propio
        protocolo de calibracion."""
        ahora = time.monotonic()
        for nombre_eje in ("x", "y"):
            estado = self._ejes[nombre_eje]
            if estado.confianza >= UMBRAL_RECALIBRACION:
                continue
            if ahora - estado.ultimo_intento_recalibracion < COOLDOWN_RECALIBRACION_SEGUNDOS:
                continue

            estado.ultimo_intento_recalibracion = ahora
            logger.info(f"[{nombre_eje}] confianza baja ({estado.confianza:.2f}), recalibrando")
            self._recalibrar_eje(nombre_eje, movedor)

    def _recalibrar_eje(self, nombre_eje: str, movedor: MovedorFn) -> None:
        direccion_positiva, direccion_negativa = list(_EJES[nombre_eje].keys())

        antes = self._fuente.tomar_snapshot()
        movedor(direccion_positiva)
        despues = self._fuente.tomar_snapshot()
        candidatos = set(direcciones_con_delta(antes, despues, DELTA_PASO))
        if not candidatos:
            self._ejes[nombre_eje].confianza = 0.0
            return

        antes2 = self._fuente.tomar_snapshot()
        movedor(direccion_positiva)
        despues2 = self._fuente.tomar_snapshot()
        candidatos &= set(direcciones_con_delta(antes2, despues2, DELTA_PASO))
        if not candidatos:
            self._ejes[nombre_eje].confianza = 0.0
            return

        antes3 = self._fuente.tomar_snapshot()
        movedor(direccion_negativa)
        despues3 = self._fuente.tomar_snapshot()
        candidatos &= set(direcciones_con_delta(antes3, despues3, -DELTA_PASO))

        if not candidatos:
            self._ejes[nombre_eje].confianza = 0.0
            return

        direccion_elegida = sorted(candidatos)[0]
        self._ejes[nombre_eje] = _EstadoEje(
            direccion_memoria=direccion_elegida,
            confianza=1.0,
            ultimo_intento_recalibracion=time.monotonic(),
        )
        logger.info(
            f"[{nombre_eje}] recalibrado: {hex(direccion_elegida)} ({len(candidatos)} candidatos)"
        )

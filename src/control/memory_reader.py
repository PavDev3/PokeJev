"""Lectura pasiva de memoria del proceso del juego (solo lectura, sin inyectar
ni ejecutar nada) para calibrar y despues leer la posicion real del jugador.

Protocolo (confirmado que funciono en el proyecto anterior, sin Game Probe):
1. Tomar una foto de la memoria heap privada y escribible del proceso.
2. Pedir al jugador que de UN paso en una direccion conocida.
3. Tomar otra foto y buscar direcciones cuyo valor cambio exactamente en +2
   (Ruby codifica enteros pequenos como Fixnum = 2n+1, asi que una casilla
   de movimiento cambia el valor crudo en memoria en exactamente 2).
4. Repetir con otra direccion perpendicular para aislar X de Y.

Es de solo lectura: nunca escribe en el proceso del juego, por lo que no hay
riesgo de crashearlo (a diferencia del Game Probe, que si inyectaba codigo).
"""

import ctypes
import logging
from ctypes import wintypes
from dataclasses import dataclass

import numpy as np
import pymem

logger = logging.getLogger(__name__)

PAGE_READWRITE = 0x04
MEM_COMMIT = 0x1000
MEM_PRIVATE = 0x20000


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", wintypes.DWORD),
        ("RegionSize", ctypes.c_size_t),
        ("State", wintypes.DWORD),
        ("Protect", wintypes.DWORD),
        ("Type", wintypes.DWORD),
    ]


def _regiones_heap(handle) -> list[tuple[int, int]]:
    """Enumera regiones de memoria heap privadas, comprometidas y escribibles."""
    regiones = []
    direccion = 0
    mbi = MEMORY_BASIC_INFORMATION()
    kernel32 = ctypes.windll.kernel32

    while direccion < 0x7FFFFFFF0000:
        resultado = kernel32.VirtualQueryEx(
            handle, ctypes.c_void_p(direccion), ctypes.byref(mbi), ctypes.sizeof(mbi)
        )
        if resultado == 0:
            break

        if (
            mbi.State == MEM_COMMIT
            and mbi.Protect == PAGE_READWRITE
            and mbi.Type == MEM_PRIVATE
            and mbi.RegionSize < 50 * 1024 * 1024  # evitar regiones gigantes, mas lento
        ):
            regiones.append((mbi.BaseAddress or 0, mbi.RegionSize))

        direccion = (mbi.BaseAddress or 0) + mbi.RegionSize

    return regiones


@dataclass
class Snapshot:
    regiones: dict[int, np.ndarray]  # direccion_base -> array de int32


def tomar_snapshot(pm: pymem.Pymem) -> Snapshot:
    regiones = {}
    for base, tamano in _regiones_heap(pm.process_handle):
        try:
            datos = pm.read_bytes(base, tamano)
        except Exception:
            continue
        n_enteros = len(datos) // 4
        if n_enteros == 0:
            continue
        arr = np.frombuffer(datos[: n_enteros * 4], dtype=np.int32)
        regiones[base] = arr
    return Snapshot(regiones=regiones)


def direcciones_con_delta(antes: Snapshot, despues: Snapshot, delta_esperado: int) -> list[int]:
    """Devuelve direcciones de memoria absolutas cuyo valor cambio exactamente
    en delta_esperado entre dos snapshots."""
    candidatos = []
    for base, arr_antes in antes.regiones.items():
        arr_despues = despues.regiones.get(base)
        if arr_despues is None or len(arr_despues) != len(arr_antes):
            continue
        diffs = arr_despues.astype(np.int64) - arr_antes.astype(np.int64)
        indices = np.where(diffs == delta_esperado)[0]
        for i in indices:
            candidatos.append(base + i * 4)
    return candidatos


@dataclass
class CoordenadasCalibradas:
    addr_x: int
    addr_y: int


def leer_entero(pm: pymem.Pymem, direccion: int) -> int:
    return pm.read_int(direccion)


class FuenteMemoriaPymem:
    """Adaptador que expone una instancia pymem.Pymem con la interfaz que
    espera RastreadorPosicion (position_tracker.py), para que ese modulo no
    tenga que acoplarse a pymem directamente y se pueda testear con fuentes
    falsas sin un proceso real."""

    def __init__(self, pm: pymem.Pymem) -> None:
        self._pm = pm

    def tomar_snapshot(self) -> Snapshot:
        return tomar_snapshot(self._pm)

    def leer_entero(self, direccion: int) -> int:
        return leer_entero(self._pm, direccion)

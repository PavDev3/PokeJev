"""Calibra automaticamente las direcciones de memoria de X e Y moviendo al
personaje y buscando el delta exacto de +2 (ver memory_reader.py).

Requiere el juego abierto y en modo exploracion (sin menus), con espacio libre
para moverse a la derecha y hacia abajo un par de casillas.
"""

import sys
import time

import pymem

sys.path.insert(0, ".")

from src.control.input_handler import mover
from src.control.memory_reader import direcciones_con_delta, tomar_snapshot


def calibrar_eje(pm: pymem.Pymem, direccion_positiva: str, direccion_negativa: str, nombre_eje: str) -> int | None:
    print(f"\n--- Calibrando eje {nombre_eje} ---")

    antes = tomar_snapshot(pm)
    mover(direccion_positiva)
    time.sleep(0.3)
    despues = tomar_snapshot(pm)
    candidatos = direcciones_con_delta(antes, despues, 2)
    print(f"Tras mover {direccion_positiva}: {len(candidatos)} candidatos con delta +2")

    if not candidatos:
        print(f"No se encontro ningun candidato para {nombre_eje}. ¿Habia espacio libre para moverse?")
        return None

    # Segunda validacion: mover otra vez en la misma direccion, deben seguir +2
    antes2 = tomar_snapshot(pm)
    mover(direccion_positiva)
    time.sleep(0.3)
    despues2 = tomar_snapshot(pm)
    candidatos2 = direcciones_con_delta(antes2, despues2, 2)
    confirmados = sorted(set(candidatos) & set(candidatos2))
    print(f"Tras repetir {direccion_positiva}: {len(confirmados)} candidatos confirmados (+2 ambas veces)")

    if not confirmados:
        print("Ningun candidato sobrevivio la segunda validacion.")
        return None

    # Tercera validacion: mover en direccion contraria, debe dar -2
    antes3 = tomar_snapshot(pm)
    mover(direccion_negativa)
    time.sleep(0.3)
    despues3 = tomar_snapshot(pm)
    candidatos_neg = set(direcciones_con_delta(antes3, despues3, -2))
    finales = sorted(set(confirmados) & candidatos_neg)
    print(f"Tras mover {direccion_negativa} (vuelta): {len(finales)} candidatos finales")

    if len(finales) == 1:
        print(f"✓ Direccion de {nombre_eje} encontrada: {hex(finales[0])}")
        return finales[0]
    elif len(finales) > 1:
        print(f"Quedan {len(finales)} candidatos, no es unico: {[hex(a) for a in finales]}")
        print(f"Usando el primero: {hex(finales[0])}")
        return finales[0]
    else:
        print(f"Ningun candidato sobrevivio las 3 validaciones para {nombre_eje}.")
        return None


def main():
    print("Buscando proceso Game.exe...")
    pm = pymem.Pymem("Game.exe")
    print(f"Adjuntado. PID: {pm.process_id}")

    print("\nAsegurate de tener espacio libre para moverte 2 casillas a la derecha")
    print("y 2 casillas hacia abajo. Presiona Enter cuando estes listo.")
    input()

    addr_x = calibrar_eje(pm, "derecha", "izquierda", "X")
    addr_y = calibrar_eje(pm, "abajo", "arriba", "Y")

    print("\n=== RESULTADO ===")
    print(f"POKEJEV_ADDR_X = {hex(addr_x) if addr_x else 'NO ENCONTRADA'}")
    print(f"POKEJEV_ADDR_Y = {hex(addr_y) if addr_y else 'NO ENCONTRADA'}")

    if addr_x and addr_y:
        with open(".env", "a", encoding="utf-8") as f:
            f.write(f"\nPOKEJEV_ADDR_X={hex(addr_x)}\n")
            f.write(f"POKEJEV_ADDR_Y={hex(addr_y)}\n")
        print("\nGuardado en .env")


if __name__ == "__main__":
    main()

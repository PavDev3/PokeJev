"""Bot de Pokemon Showdown: inicia sesion con tu cuenta, busca UNA batalla en
la ladder publica, la juega con Jev, y se detiene solo al terminar.

Uso: python -m showdown.main
Pide usuario y contrasena de forma interactiva (la contrasena no se muestra
al escribirla y nunca se guarda).
"""

import asyncio
import getpass
import json
import logging

from showdown.client import ClienteShowdown, parsear_request
from showdown.decision import decidir_accion
from showdown.estado import parsear_estado

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("showdown/showdown_bot.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

FORMATO = "gen9randombattle"


async def manejar_turno(cliente: ClienteShowdown, room_id: str, request_json: dict) -> None:
    if request_json.get("wait"):
        return

    estado = parsear_estado(request_json)
    tipo, indice = decidir_accion(estado)
    await cliente.elegir(room_id, f"{tipo} {indice}")


def hacer_manejador(cliente: ClienteShowdown, batalla_terminada: asyncio.Event):
    sala_batalla: dict[str, str | None] = {"id": None}

    async def manejador(room_id: str, linea: str) -> None:
        logger.debug(f"[{room_id}] {linea}")

        if room_id.startswith("battle-") and sala_batalla["id"] is None:
            sala_batalla["id"] = room_id
            logger.info(f"=== Batalla encontrada: {room_id} ===")

        if linea.startswith("|request|"):
            request_json = parsear_request(linea)
            if request_json:
                await manejar_turno(cliente, room_id, request_json)

        elif linea.startswith("|win|") or linea.startswith("|tie|"):
            if linea.startswith("|win|"):
                ganador = linea[len("|win|") :]
                logger.info(f"=== Batalla terminada. Gano: {ganador} ===")
            else:
                logger.info("=== Batalla terminada en empate ===")
            batalla_terminada.set()

        elif linea.startswith("|error|"):
            logger.error(f"Error del servidor: {linea}")

        elif linea.startswith("|updatesearch|"):
            datos = json.loads(linea[len("|updatesearch|") :])
            if not datos.get("searching") and sala_batalla["id"] is None:
                logger.info("Esperando a encontrar rival en la ladder...")

    return manejador


async def main() -> None:
    nombre_usuario = input("Usuario de Pokemon Showdown: ").strip()
    password = getpass.getpass("Contrasena: ")

    logger.info(f"=== Bot de Showdown iniciado como '{nombre_usuario}' ===")
    cliente = ClienteShowdown(nombre_usuario=nombre_usuario, password=password)
    batalla_terminada = asyncio.Event()

    async def conectar_y_jugar():
        await cliente.conectar(hacer_manejador(cliente, batalla_terminada))

    tarea_conexion = asyncio.create_task(conectar_y_jugar())

    await asyncio.sleep(2)  # dar tiempo a que el login termine antes de buscar
    await cliente.buscar_batalla(FORMATO)
    logger.info(f"Buscando batalla en '{FORMATO}'... abre play.pokemonshowdown.com para verla.")

    await batalla_terminada.wait()
    logger.info("Batalla terminada, deteniendo el bot.")
    tarea_conexion.cancel()


if __name__ == "__main__":
    asyncio.run(main())

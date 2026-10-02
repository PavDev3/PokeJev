"""Cliente de Pokemon Showdown: conexion WebSocket, login sin registrar
(nombre temporal, sin contrasena) y manejo basico del protocolo de texto.

Protocolo: https://github.com/smogon/pokemon-showdown/blob/master/PROTOCOL.md
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Awaitable, Callable

import requests
import websockets

logger = logging.getLogger(__name__)

SERVIDOR_WS = "wss://sim3.psim.us/showdown/websocket"
ACTION_URL = "https://play.pokemonshowdown.com/action.php"

ManejadorMensaje = Callable[[str, str], Awaitable[None]]  # (room_id, linea) -> None


@dataclass
class ClienteShowdown:
    nombre_usuario: str
    password: str | None = None
    _ws: object = None
    _manejador: ManejadorMensaje | None = None

    async def conectar(self, manejador: ManejadorMensaje) -> None:
        self._manejador = manejador
        self._ws = await websockets.connect(SERVIDOR_WS, max_size=None)
        await self._escuchar()

    async def _escuchar(self) -> None:
        async for mensaje in self._ws:
            await self._procesar_mensaje(mensaje)

    async def _procesar_mensaje(self, mensaje: str) -> None:
        room_id = ""
        if mensaje.startswith(">"):
            primera_linea, _, resto = mensaje.partition("\n")
            room_id = primera_linea[1:]
            mensaje = resto

        for linea in mensaje.split("\n"):
            if not linea:
                continue
            if linea.startswith("|challstr|"):
                await self._login(linea[len("|challstr|") :])
                continue
            await self._manejador(room_id, linea)

    async def _login(self, challstr: str) -> None:
        if self.password:
            assertion = await self._login_con_password(challstr)
        else:
            assertion = await self._login_sin_registrar(challstr)

        await self.enviar_global(f"/trn {self.nombre_usuario},0,{assertion}")
        logger.info(f"Login enviado como '{self.nombre_usuario}'")

    async def _login_con_password(self, challstr: str) -> str:
        """Login con cuenta registrada (usuario + password reales)."""
        respuesta = await asyncio.to_thread(
            requests.post,
            ACTION_URL,
            data={
                "act": "login",
                "name": self.nombre_usuario,
                "pass": self.password,
                "challstr": challstr,
            },
        )
        texto = respuesta.text
        if texto.startswith("]"):
            texto = texto[1:]
        datos = json.loads(texto)

        if not datos.get("actionsuccess"):
            raise RuntimeError(f"Login fallido para '{self.nombre_usuario}': {datos}")

        return datos["assertion"]

    async def _login_sin_registrar(self, challstr: str) -> str:
        """Login sin contrasena: nombre temporal, falla si esta registrado por otra persona."""
        respuesta = await asyncio.to_thread(
            requests.post,
            ACTION_URL,
            data={
                "act": "getassertion",
                "userid": self.nombre_usuario.lower(),
                "challstr": challstr,
            },
        )
        assertion = respuesta.text
        if assertion.startswith("]"):
            assertion = assertion[1:]

        if assertion == ";":
            raise RuntimeError(
                f"El nombre '{self.nombre_usuario}' esta registrado por otra persona; "
                "elige otro nombre o usa password."
            )
        return assertion

    async def buscar_batalla(self, formato: str) -> None:
        await self.enviar_global(f"/search {formato}")
        logger.info(f"Buscando batalla en la ladder: {formato}")

    async def enviar_global(self, comando: str) -> None:
        await self._ws.send(comando)

    async def enviar_a_sala(self, room_id: str, comando: str) -> None:
        await self._ws.send(f"{room_id}|{comando}")

    async def aceptar_reto(self, usuario_retador: str) -> None:
        await self.enviar_global(f"/accept {usuario_retador}")
        logger.info(f"Reto aceptado de '{usuario_retador}'")

    async def elegir(self, room_id: str, eleccion: str) -> None:
        """eleccion: ej. 'move 1', 'switch 2'."""
        await self.enviar_a_sala(room_id, f"/choose {eleccion}")


def parsear_request(linea_request: str) -> dict | None:
    """|request|<json> -- el json puede venir vacio (fin de turno sin decision)."""
    datos = linea_request[len("|request|") :]
    if not datos:
        return None
    return json.loads(datos)

"""Captura solo el area de cliente de la ventana del juego (sin barra de titulo de Windows).

No depende de donde este posicionada la ventana en pantalla -- la localiza por su
titulo y recorta exactamente su contenido, para que las coordenadas calibradas en
calibration/anchors.json sean siempre validas independientemente de la posicion.
"""

import mss
import numpy as np
import win32gui

_REQUERIDOS = ("pok", "4.0")  # evita caracteres especiales (ñ/é) en el match
_EXCLUIDOS = ("explorador", "archivos", "visual studio", "code")


class VentanaNoEncontradaError(Exception):
    pass


def encontrar_ventana() -> int:
    """Busca la ventana del juego por coincidencia parcial de titulo (case-insensitive,
    sin depender de caracteres especiales como n/e), excluyendo ventanas que
    comparten palabras del titulo pero no son el juego (ej. el Explorador de
    archivos con la carpeta del juego abierta, o el editor de codigo)."""
    encontrada = []

    def _callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            texto = win32gui.GetWindowText(hwnd).lower()
            if all(req in texto for req in _REQUERIDOS) and not any(
                exc in texto for exc in _EXCLUIDOS
            ):
                encontrada.append(hwnd)

    win32gui.EnumWindows(_callback, None)

    if not encontrada:
        raise VentanaNoEncontradaError(
            "No se encontro la ventana del juego (busca titulo con 'pok' y '4.0')"
        )
    return encontrada[0]


def area_cliente(hwnd: int) -> tuple[int, int, int, int]:
    """Rectangulo (x1, y1, x2, y2) del area de cliente en coordenadas de pantalla
    (excluye barra de titulo y bordes de la ventana)."""
    left, top = win32gui.ClientToScreen(hwnd, (0, 0))
    right, bottom = win32gui.GetClientRect(hwnd)[2], win32gui.GetClientRect(hwnd)[3]

    if left <= -30000 or top <= -30000:
        raise VentanaNoEncontradaError(
            "La ventana del juego esta minimizada -- restaurala antes de capturar."
        )

    return left, top, left + right, top + bottom


def enfocar_ventana() -> None:
    """Trae la ventana del juego al frente y le da el foco de teclado.

    Windows bloquea SetForegroundWindow si el proceso que lo pide no estaba ya
    en primer plano. El truco estandar: simular una pulsacion de Alt primero,
    que Windows acepta como señal de "intencion real del usuario".
    """
    import win32api
    import win32con

    hwnd = encontrar_ventana()
    win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)
    win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)
    win32gui.SetForegroundWindow(hwnd)


def capturar_juego() -> np.ndarray:
    """Devuelve la captura actual del contenido del juego como array BGR (formato OpenCV)."""
    hwnd = encontrar_ventana()
    x1, y1, x2, y2 = area_cliente(hwnd)

    with mss.mss() as sct:
        monitor = {"left": x1, "top": y1, "width": x2 - x1, "height": y2 - y1}
        captura = np.array(sct.grab(monitor))

    return captura[:, :, :3]  # descarta canal alpha, deja BGR

"""Extrae texto de las regiones calibradas usando EasyOCR.

Tesseract no sirve para la fuente pixel-art del juego (probado, falla incluso con
recortes grandes y limpios). EasyOCR funciona bastante mejor, pero con baja confianza
y errores de caracteres comunes (o/0, l/1, etc.) -- por eso cada extractor aplica
limpieza con regex en vez de confiar en el texto crudo.
"""

import re

import easyocr

_reader: easyocr.Reader | None = None


def _get_reader() -> easyocr.Reader:
    global _reader
    if _reader is None:
        _reader = easyocr.Reader(["es", "en"], gpu=True, verbose=False)
    return _reader


def leer_texto(imagen_bgr) -> list[str]:
    """Devuelve todos los fragmentos de texto detectados en la imagen, sin procesar."""
    resultados = _get_reader().readtext(imagen_bgr)
    return [texto for _, texto, _ in resultados]


def extraer_nombre(fragmentos: list[str]) -> str:
    """Primera 'palabra' alfabetica larga (>=3 letras) del primer fragmento util.
    EasyOCR a veces junta nombre+nivel en un mismo fragmento (ej. 'Skelzdige gNul4'),
    por eso se toma solo el primer token, no todo el fragmento limpio de digitos."""
    for frag in fragmentos:
        primera_palabra = frag.split()[0] if frag.split() else ""
        limpio = re.sub(r"[^A-Za-zÀ-ÿ]", "", primera_palabra)
        if len(limpio) >= 3:
            return limpio.capitalize()
    return ""


def extraer_nivel(fragmentos: list[str]) -> int | None:
    """Busca un patron tipo 'Nv.14' o similar en los fragmentos."""
    for frag in fragmentos:
        m = re.search(r"[Nn][vV].?\s*(\d+)", frag)
        if m:
            return int(m.group(1))
    return None


_CONFUSIONES_DIGITOS = str.maketrans({"o": "0", "O": "0", "l": "1", "I": "1"})
_PARECE_NUMERICO = re.compile(r"^[0-9oOlI%/\s]+$")


def _candidatos_numericos(fragmentos: list[str]) -> list[str]:
    """Filtra solo los fragmentos compuestos casi enteramente por digitos/caracteres
    confundibles con digitos -- evita que letras de un nombre (ej. la 'l' de 'Skrel')
    se confundan con un '1' al aplicar la correccion de OCR."""
    return [f for f in fragmentos if _PARECE_NUMERICO.match(f.strip())]


def extraer_porcentaje_hp(fragmentos: list[str]) -> int | None:
    """Busca un porcentaje tipo '100%' (o '1o0/', confusion comun de OCR) y lo normaliza.
    Ignora fragmentos tipo '350/350' (HP absoluto, no porcentaje). Prioriza fragmentos
    con marcador explicito de porcentaje ('%' o '/' sin otro numero detras) sobre
    digitos sueltos, que suelen ser una lectura fallida del nivel (ej. 'Nv.5' -> 'l5')."""
    candidatos = _candidatos_numericos(fragmentos)
    con_marcador = [f for f in candidatos if "%" in f or f.rstrip().endswith("/")]

    for grupo in (con_marcador, candidatos):
        for frag in grupo:
            if re.search(r"\d+\s*/\s*\d+", frag):
                continue  # es HP absoluto (actual/maximo), no porcentaje
            candidato = frag.translate(_CONFUSIONES_DIGITOS)
            m = re.search(r"\d{1,3}", candidato)
            if m:
                valor = int(m.group(0))
                if 0 <= valor <= 100:
                    return valor
    return None


def extraer_nombre_movimiento(fragmentos: list[str]) -> str:
    """Junta todos los fragmentos de texto del boton de un movimiento. El nombre puede
    venir partido en fragmentos separados (ej. 'Envite' + 'mgneo') o en uno solo con
    espacio interno (ej. 'Canto Ardiente') -- se preservan los espacios en ambos casos."""
    palabras = []
    for frag in fragmentos:
        for palabra in frag.split():
            limpia = re.sub(r"[^A-Za-zÀ-ÿ]", "", palabra)
            if limpia:
                palabras.append(limpia.capitalize())
    return " ".join(palabras)


def extraer_pp(fragmentos: list[str]) -> tuple[int, int] | None:
    """Busca un patron 'PP: X/Y' (tolerante a confusiones o/0, l/1)."""
    for frag in fragmentos:
        candidato = frag.translate(_CONFUSIONES_DIGITOS)
        m = re.search(r"(\d{1,2})\s*/\s*(\d{1,2})", candidato)
        if m:
            return int(m.group(1)), int(m.group(2))
    return None


def extraer_hp_absoluto(fragmentos: list[str]) -> tuple[int, int] | None:
    """Busca un patron 'actual/maximo' (ej. '350/350') para el HP del propio equipo."""
    for frag in _candidatos_numericos(fragmentos):
        candidato = frag.translate(_CONFUSIONES_DIGITOS)
        m = re.search(r"(\d{1,4})\s*/\s*(\d{1,4})", candidato)
        if m:
            return int(m.group(1)), int(m.group(2))
    return None

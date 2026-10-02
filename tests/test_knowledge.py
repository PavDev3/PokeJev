"""Tests de traduccion de movimientos y efectividad real contra tipos de enemigo."""

from src.decision.state_builder import EstadoCombate, construir_estado_texto
from src.knowledge.pokedex import describir_efectividad, tipos_de, traducir_movimiento


def test_traduce_movimientos_vistos_en_combate_real():
    assert traducir_movimiento("Ascuas") == "Ember"
    assert traducir_movimiento("Envite Igneo") == "Flare-Blitz"
    assert traducir_movimiento("Bostezo") == "Yawn"


def test_canto_ardiente_no_tiene_traduccion_conocida():
    # No es un movimiento real de los juegos Pokemon (posible nombre de fangame/randomizer).
    assert traducir_movimiento("Canto Ardiente") is None


def test_traduccion_tolera_falta_de_tildes_del_ocr():
    assert traducir_movimiento("Envite Igneo") == traducir_movimiento("Envite Ígneo")


def test_tipos_de_pokemon_vistos_hoy():
    assert tipos_de("Cherubi") == ["Grass"]
    assert tipos_de("Skrelp") == ["Poison", "Water"]
    assert tipos_de("Skeledirge") == ["Fire", "Ghost"]


def test_pokemon_desconocido_devuelve_lista_vacia():
    assert tipos_de("PokemonQueNoExiste") == []


def test_efectividad_real_fuego_vs_planta():
    descripcion = describir_efectividad("Ascuas", tipos_de("Cherubi"))
    assert "muy efectivo" in descripcion


def test_efectividad_con_movimiento_sin_datos_no_falla():
    descripcion = describir_efectividad("Canto Ardiente", ["Grass"])
    assert "datos de tipo desconocidos" in descripcion


def test_estado_completo_incluye_tipos_y_efectividad_real():
    estado = EstadoCombate(
        enemigo_nombre="Cherubi",
        enemigo_hp_pct=100,
        jugador_nombre="Skeledirge",
        jugador_hp_actual=350,
        jugador_hp_maximo=350,
        movimientos=["Ascuas", "Canto Ardiente"],
    )
    texto = construir_estado_texto(estado)
    assert "Tipos del enemigo: Grass" in texto
    assert "muy efectivo" in texto
    assert "datos de tipo desconocidos" in texto

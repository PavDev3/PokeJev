from showdown.estado import parsear_estado

REQUEST_COMBATE_NORMAL = {
    "active": [
        {
            "moves": [
                {"move": "Tackle", "id": "tackle", "pp": 35, "maxpp": 35, "disabled": False},
                {"move": "Thunderbolt", "id": "thunderbolt", "pp": 0, "maxpp": 15, "disabled": False},
            ]
        }
    ],
    "side": {
        "pokemon": [
            {"details": "Pikachu, L88, M", "condition": "120/120", "active": True},
            {"details": "Charizard, L82, M", "condition": "0 fnt", "active": False},
            {"details": "Blastoise, L80, F", "condition": "95/150", "active": False},
        ]
    },
}

REQUEST_FORCE_SWITCH = {
    "forceSwitch": [True],
    "side": {
        "pokemon": [
            {"details": "Pikachu, L88, M", "condition": "0 fnt", "active": True},
            {"details": "Blastoise, L80, F", "condition": "95/150", "active": False},
        ]
    },
}


def test_parsea_movimientos_disponibles():
    estado = parsear_estado(REQUEST_COMBATE_NORMAL)
    nombres = [m.nombre for m in estado.movimientos]
    assert nombres == ["Tackle", "Thunderbolt"]
    assert not estado.debe_cambiar


def test_movimiento_sin_pp_queda_marcado():
    estado = parsear_estado(REQUEST_COMBATE_NORMAL)
    thunderbolt = next(m for m in estado.movimientos if m.nombre == "Thunderbolt")
    assert thunderbolt.pp == 0


def test_pokemon_activo_no_se_puede_cambiar():
    estado = parsear_estado(REQUEST_COMBATE_NORMAL)
    activo = next(p for p in estado.equipo if p.activo)
    assert activo.nombre == "Pikachu"
    assert not activo.puede_cambiar


def test_pokemon_debilitado_no_se_puede_cambiar():
    estado = parsear_estado(REQUEST_COMBATE_NORMAL)
    charizard = next(p for p in estado.equipo if p.nombre == "Charizard")
    assert not charizard.puede_cambiar


def test_force_switch_no_expone_movimientos():
    estado = parsear_estado(REQUEST_FORCE_SWITCH)
    assert estado.debe_cambiar
    assert estado.movimientos == []
    disponibles = [p.nombre for p in estado.equipo if p.puede_cambiar]
    assert disponibles == ["Blastoise"]

# PokeJev

Bots que juegan Pokemon usando [Jev](https://typesafe.ai) (typesafe-sdk) como motor de decision:

- **Pokemon Anil** (`src/`): un fangame RPG Maker, leido con vision clasica (OpenCV + EasyOCR) -- sin modelos de IA de vision ni inyeccion de codigo en el proceso del juego.
- **Pokemon Showdown** (`showdown/`): juega batallas reales contra otros jugadores en la ladder publica, via el protocolo de texto de Showdown -- sin vision ni memoria, el estado llega ya estructurado.

## Arquitectura

```
Captura pantalla (mss, solo area de cliente de la ventana)
       |
Vision clasica (template matching para clasificar pantalla + EasyOCR para texto)
       |
Construccion del estado en texto (+ conocimiento: tipos, efectividad, traduccion ES->EN)
       |
Jev decide (Choice: menu -> movimiento en combate)
       |
pynput ejecuta (flechas + Enter + navegacion de menu en cuadricula)
```

## Estructura

```
src/
├── main.py                  # bucle principal
├── vision/                  # captura, clasificacion de pantalla, OCR, deteccion de movimiento
├── decision/                # cliente de Jev, construccion del estado de combate
├── control/                 # input (pynput), lectura de memoria (posicion, experimental)
└── knowledge/                # pokedex, tipos, traduccion de movimientos ES->EN
calibration/                  # capturas de referencia y plantillas de deteccion
scripts/                      # calibracion de memoria, wizard de Cheat Engine
tests/
```

## Instalar

```bash
pip install -r requirements.txt
```

Tesseract no es necesario (se usa EasyOCR), pero si quieres usar el script de calibracion de memoria opcional hace falta [Cheat Engine](https://www.cheatengine.org/) para encontrar direcciones manualmente.

Configura la API key de Jev como variable de entorno `TYPESAFE_API_KEY`.

## Correr

```bash
python -m src.main
```

Requiere el juego abierto (ventana con titulo que contenga "Pok" y "4.0").

## Estado del proyecto

| Fase | Estado |
|---|---|
| Vision (clasificacion + OCR) | Completa |
| Combate con Jev | Completa, probada en vivo |
| Dialogos | Completa (avance automatico) |
| Exploracion | Basica -- anti-stuck por deteccion de colision de fotogramas, sin posicion real ni objetivo dirigido |
| Posicion real (x/y/map_id) | Experimental, no confiable todavia -- ver `src/control/position_tracker.py` |

### Por que no hay posicion real todavia

El motor del juego es RPG Maker con RGSS (Ruby). La posicion del jugador es un atributo de un objeto Ruby en el heap, y el recolector de basura (GC) mueve/reutiliza esa memoria en cuestion de segundos. Se descarto una tecnica de inyeccion de codigo (tipo "Game Probe") por invasiva y porque fallaba en la practica. La alternativa actual (`src/control/memory_reader.py` + `src/control/position_tracker.py`) usa solo lectura pasiva de memoria (sin inyectar ni ejecutar nada) con un protocolo de calibracion por movimiento y recalibracion automatica cuando la confianza cae -- el diseño esta testeado con mocks, pero falta validarlo extensamente en vivo contra el juego real.

### Limitacion conocida de la pokedex

El juego es un randomizer/fangame que incluye Pokemon de generaciones mas alla de la 1. La base de conocimiento cubre 154 Pokemon (151 de Gen1 + los vistos en combates reales) y 83 movimientos traducidos de español a ingles -- se amplia segun se encuentren nuevos casos.

## Pokemon Showdown

Juega UNA batalla en la ladder publica (Random Battle) con tu propia cuenta y se detiene solo al terminar.

```bash
python -m showdown.main
```

Pide usuario y contrasena de forma interactiva (la contrasena no se muestra al escribirla y no se guarda en ningun archivo). Mientras corre, abre [play.pokemonshowdown.com](https://play.pokemonshowdown.com) para ver la batalla en vivo.

Para jugar otra batalla, vuelve a correr el comando.

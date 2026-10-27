# Analizador de catálogo musical

**Autor:** Alejo Bazan Forti

**Materia:** Programación Orientada a Datos — Trabajo Práctico 2 (individual)

**Carrera:** Licenciatura en Ciencia de Datos — Universidad Católica Argentina (UCA)

## Problema

Quien arma rankings, listas de reproducción o actividades sobre música suele recibir catálogos de canciones en archivos CSV o JSON con errores de carga: identificadores mal escritos o repetidos, duraciones imposibles, métricas negativas, valores fuera de rango y datos faltantes. Revisar esos archivos y responder consultas a mano es lento, propenso a errores y difícil de repetir.

## Usuario

Un aficionado a la música, un curador de listas o un docente que necesita validar un catálogo y consultarlo desde la consola de forma rápida y repetible, sabiendo qué filas se descartaron o corrigieron y por qué.

## Solución propuesta

Una aplicación de línea de comandos en Python, construida solo con la biblioteca estándar, que:

1. lee un catálogo en CSV o JSON con la misma interfaz;
2. normaliza los textos, valida el esquema y las reglas de cada fila, y registra las filas **rechazadas** y las filas **ajustadas** con su motivo;
3. ejecuta una de cinco operaciones de consulta sobre las canciones válidas;
4. verifica el resultado y lo exporta a CSV en `outputs/`.

## Operaciones disponibles

| Comando | Para qué sirve |
|---|---|
| `resumen` | Cantidad de canciones, artistas y álbumes, conteo por tipo de lanzamiento, duración y energía medias, y totales y promedio de streams. |
| `filtrar` | Busca canciones por artista, tipo de lanzamiento, duración o cantidad mínima de streams. Los filtros se pueden combinar. |
| `top` | Ordena las canciones por streams de mayor a menor. Se puede indicar cuántas mostrar y limitar el ranking a un artista. |
| `albumes` | Suma los streams disponibles por álbum y muestra el de mayor total para cada artista. |
| `comparar` | Compara dos artistas en cantidad de canciones, streams, duración media y energía media, e indica quién lidera en cada métrica. |

## Alcance de la versión 1

**Incluye:** lectura de CSV y JSON, limpieza auditada, cinco consultas, verificación de resultados y exportación a CSV. Los archivos de `data/` nunca se modifican.

**Queda fuera:** interfaz web o gráfica, gráficos, aprendizaje automático, consultas a APIs en vivo, análisis de letras o audio, bases de datos y modificación del catálogo.

## Resultado y cómo interpretarlo

Cada ejecución muestra primero una **auditoría** (filas leídas, aceptadas, rechazadas y ajustadas, con el detalle de cada una) y después el resultado de la operación en una tabla de texto. Los mismos datos se exportan a `outputs/`:

- `resultado_<operacion>.csv`: el resultado de la consulta.
- `rechazos.csv`: filas descartadas (`nro_fila`, `id_cancion`, `motivo`).
- `ajustes.csv`: filas aceptadas pero corregidas (`nro_fila`, `id_cancion`, `campo`, `valor_original`, `accion`).

Los totales y promedios de streams se calculan **solo sobre las canciones con dato disponible**, y el resultado informa cuántas son (`canciones_con_streams`). Conviene leer siempre esa columna: un álbum o un artista con pocas canciones con dato queda subestimado.

## Datos

- **Fuente:** dataset *Spotify dataset* publicado por el usuario `sanjanchaudhari` en Kaggle (<https://www.kaggle.com/datasets/sanjanchaudhari/spotify-dataset>), archivo `cleaned_dataset.csv` (20.594 filas y 24 columnas).
- **Recorte utilizado:** 80 canciones, diez de cada uno de estos ocho artistas: Oasis, Bon Jovi, Elton John, The Beatles, Mac Miller, Queen, Red Hot Chili Peppers y Pink Floyd.
- **Unidad de análisis:** cada fila (o cada objeto del JSON) es **una canción de un artista**.
- **Variables:** `id_cancion`, `artista`, `cancion`, `album`, `tipo_album`, `duracion_min`, `streams`, `views`, `likes` y `energy`.
- **Formatos:** `data/canciones.csv` y `data/canciones.json` contienen los mismos 80 registros. `data/canciones_con_errores.csv` y `.json` agregan filas de prueba para demostrar la validación.
- **Licencia, fecha de consulta, procedimiento y diccionario de variables:** ver [`data/README.md`](data/README.md).

El `id_cancion` (por ejemplo `QUE-003`) fue creado para este trabajo; no es un código oficial de Spotify ni un ISRC.

## Requisitos e instalación

- Python 3.10 o superior (`python --version`).
- No hay que instalar nada: se usan solo módulos de la biblioteca estándar (`csv`, `json`, `re`, `argparse`, `dataclasses`, `abc`, `statistics`, `unittest`).
- Abrí una terminal en la carpeta raíz del proyecto; todos los comandos se ejecutan desde ahí.

## Cómo ejecutar el programa

Desde la carpeta raíz del proyecto, podés ejecutar el mismo análisis con CSV y con JSON. **La única diferencia es el archivo indicado después de `--entrada`.**

```powershell
# Ejecutar el resumen con CSV
python -m src.main --entrada data/canciones.csv resumen

# Ejecutar el mismo resumen con JSON
python -m src.main --entrada data/canciones.json resumen

# Otras operaciones
python -m src.main --entrada data/canciones.csv top --n 5
python -m src.main --entrada data/canciones.json filtrar --artista Queen --dur-min 3 --dur-max 6
python -m src.main --entrada data/canciones.csv albumes
python -m src.main --entrada data/canciones.json comparar --artista1 Queen --artista2 Oasis

# Probar el archivo con errores en ambos formatos
python -m src.main --entrada data/canciones_con_errores.csv resumen
python -m src.main --entrada data/canciones_con_errores.json resumen
```

`--entrada` indica el archivo (`.csv` o `.json`; por defecto `data/canciones.csv`) y `--salida-dir` la carpeta de salida (por defecto `outputs`). Ambas opciones van **antes** del nombre de la operación. Si hay un error esperado (archivo inexistente, parámetro inválido, artista que no existe), el programa muestra un mensaje claro y termina con código distinto de 0.

## Pruebas

```bash
python -m unittest discover -s tests -t . -v
```

La suite tiene 28 pruebas que cubren:

- **Casos normales:** métodos de `Cancion`, filtros, ranking, álbum más escuchado y comparación con valores conocidos.
- **Entradas inválidas y casos límite:** identificadores mal formados o duplicados, duración y energía en los bordes del rango, streams negativos o no numéricos, archivos inexistentes, vacíos o mal formados, columnas faltantes, CSV o JSON guardados con BOM.
- **Propiedades del resultado:** CSV y JSON producen exactamente las mismas canciones, rechazos y ajustes; leídas = aceptadas + rechazadas; la suma de streams por álbum coincide con el cálculo independiente; el álbum elegido es realmente el máximo; el ranking está ordenado; dos ejecuciones dan resultados idénticos.

## Organización del código y decisiones de diseño

```text
.
├── README.md
├── requirements.txt
├── .gitignore
├── src/
│   ├── __init__.py
│   ├── fuentes.py      # lectura de CSV y JSON
│   ├── pipeline.py     # dominio, normalización, validación, operaciones y exportación
│   └── main.py         # línea de comandos y coordinación del flujo
├── tests/
│   ├── __init__.py
│   └── test_app.py
├── data/
│   ├── README.md
│   ├── canciones.csv
│   ├── canciones.json
│   ├── canciones_con_errores.csv
│   └── canciones_con_errores.json
└── outputs/            # resultados de ejecución (no se versionan)
    └── .gitkeep
```

**Flujo:** `cargar` → `normalizar_campos` → `validar_esquema` → `limpiar_datos` → operación → `verificar_resultado` → `guardar_resultado`, `guardar_rechazos` y `guardar_ajustes`. Cada etapa es una función con una sola responsabilidad.

**`FuenteDatos` (clase base abstracta) con `FuenteCSV` y `FuenteJSON`.** Define un contrato único, `cargar(ruta) -> list[dict]`. El resto del programa recibe siempre la misma estructura y no depende del formato del archivo; agregar un formato nuevo sería sumar una clase hija sin tocar la lógica. `obtener_fuente(ruta)` elige la clase según la extensión. Ambas leen con `utf-8-sig` para tolerar el BOM que Excel agrega en Windows.

**`Cancion` (dataclass inmutable).** Representa una fila ya validada, con sus datos y métodos propios (`duracion_mmss`, `streams_millones`, `tiene_datos_faltantes`, `a_dict`). Es `frozen` porque después de la limpieza sus valores no deberían cambiar. No lee ni escribe archivos.

**Expresión regular más comprobaciones complementarias.** `id_cancion` se valida con `[A-Z]{3}-\d{3}` aplicada con `fullmatch` (tres letras mayúsculas, un guion y tres dígitos). La expresión solo comprueba el formato del texto, así que se complementa con lo que no puede resolver: que el prefijo corresponda al artista (mapa `OAS` → Oasis, `QUE` → Queen, etc.) y que el identificador no esté repetido.

**`limpiar_datos` coordina funciones pequeñas.** Cada regla vive en su propia función (`_motivo_identificador`, `_motivo_textos`, `_leer_duracion`, `_leer_enteros`, `_leer_energy`) y `_validar_fila` las aplica en orden hasta la primera que falla.

**`verificar_resultado`** comprueba propiedades con un cálculo distinto del que produjo el resultado (por ejemplo, vuelve a sumar los streams por álbum y revisa que el elegido sea el máximo), para que la verificación pueda fallar de verdad.

## Decisiones de limpieza

**Normalización (`normalizar_campos`).** Se eliminan espacios al principio y al final, se colapsan los espacios repetidos, y los campos vacíos del CSV y los `null` del JSON pasan a `None`. Los números se convierten a `int` o `float`; un valor inválido (`"abc"`, `"12.5"` en un campo entero) se conserva tal cual para que `limpiar_datos` lo rechace con un motivo explícito. Así CSV y JSON llegan con la misma representación.

**Rechazo de filas.** Cada fila inválida produce un único rechazo, con el primer motivo encontrado según este orden: (1) formato del `id_cancion`; (2) prefijo del id coherente con el artista; (3) id repetido (se conserva la primera aparición); (4) `artista`, `cancion` y `album` no vacíos; (5) `tipo_album` en {`album`, `single`, `compilation`}; (6) `duracion_min` numérica y entre 0,5 y 30; (7) `streams`, `views` y `likes` enteros mayores o iguales a 0 cuando existen; (8) `energy` numérica y entre 0 y 1.

**Datos opcionales.** `streams`, `views` y `likes` pueden faltar: la fila se acepta y el valor queda en `None`. Nunca se reemplaza por 0.

**`streams = 0` se interpreta como dato no disponible.** En el recorte hay 13 canciones con `streams = 0` (nueve de las diez de Pink Floyd, tres de Oasis y una de Queen). Se asume que ese cero indica un dato ausente en la fuente y no cero reproducciones reales, así que se convierte en `None` y cada cambio queda en `ajustes.csv`. Es una **suposición del trabajo**: la fuente no permite demostrarla y puede modificar totales y rankings.

**Textos corregidos.** Si la normalización cambia un texto (por ejemplo `"Queen "` pasa a `"Queen"`), el cambio se registra en `ajustes.csv`. Ninguna corrección es silenciosa.

## Ejemplo de resultado e interpretación

Auditoría de `data/canciones_con_errores.csv`:

```text
Filas leídas     : 87
Filas aceptadas  : 80
Filas rechazadas : 7
Filas ajustadas  : 14
```

Las siete filas rechazadas (81 a 87) corresponden a: id con formato inválido, id duplicado, duración 0, streams negativos, energía fuera de rango, tipo de álbum no permitido y título vacío. Las 14 filas ajustadas son las 13 con `streams = 0` y el texto normalizado de `QUE-001`.

Comparación de dos artistas (`comparar --artista1 Queen --artista2 Oasis`, sobre `data/canciones.json`):

```text
artista | cantidad_canciones | canciones_con_streams | streams_totales | streams_promedio | duracion_media_min | energy_media
-----------------------------------------------------------------------------------------------------------------------------
Queen   | 10                 | 9                     | 9384533757      | 1042725973       | 3.79               | 0.581
Oasis   | 10                 | 7                     | 2558836850      | 365548121.43     | 4.72               | 0.769
LÍDER   | Empate             | Queen                 | Queen           | Queen            | Oasis              | Oasis
```

**Cómo leerlo:** Queen acumula más streams totales y también más streams por canción, y sus canciones son más cortas (3,79 contra 4,72 minutos). Oasis tiene una energía media más alta. Como Queen tiene 9 canciones con dato y Oasis 7, el promedio por canción es la comparación más justa que el total.

Otros valores de referencia sobre `data/canciones.csv`: 80 canciones, 8 artistas, 47 álbumes distintos, 67 canciones con streams, 36.387.534.829 streams en total, duración media de 4,34 minutos y energía media de 0,613. La canción más escuchada es `QUE-003`, "Bohemian Rhapsody - Remastered 2011", con 2.038.872.787 streams.

## Limitaciones

- El catálogo incluye solo ocho artistas muy conocidos y diez canciones por artista; no es una muestra representativa de toda la música de Spotify.
- Los resultados dependen del recorte y de los valores del dataset en la fecha de consulta; no se consultan datos en vivo.
- Tratar `streams = 0` como dato faltante es una suposición y puede cambiar totales y rankings. Pink Floyd queda con una sola canción con dato, por lo que su álbum "más escuchado" se basa en esa única canción.
- Los nombres de álbum corresponden a ediciones específicas (por ejemplo "Deluxe" o "Remastered"); dos ediciones de un mismo disco se cuentan por separado.
- `views` y `likes` provienen de métricas de videos asociadas a las canciones; el método con el que el dataset original las vinculó no está documentado en los archivos disponibles.

## Versión entregada

La versión evaluada se identifica con la etiqueta `v1.1` del repositorio (`git show v1.1`).

# Documentación de los datos

## Origen y procedencia

| Ítem | Detalle |
|---|---|
| **Fuente** | Dataset *Spotify dataset* en Kaggle |
| **URL** | <https://www.kaggle.com/datasets/sanjanchaudhari/spotify-dataset> |
| **Publicado por** | Usuario de Kaggle `sanjanchaudhari` |
| **Archivo original** | `cleaned_dataset.csv` (20.594 filas y 24 columnas). No se incluye en este repositorio. |
| **Responsable del recorte y de este repositorio** | Alejo Bazan Forti |
| **Licencia** | [Open Data Commons Public Domain Dedication and License (PDDL) v1.0]. |
| **Fecha de consulta** | 26/10/2026. |
| **Condiciones de uso** | Uso académico, sujeto a la licencia indicada arriba. No se redistribuye el archivo original completo, solo un recorte de 80 canciones. |

Las columnas originales `Channel`, `Licensed` y `official_video` indican que `views` y `likes` provienen de videos de YouTube asociados a cada canción, mientras que `streams` y `energy` corresponden a métricas de Spotify. Las condiciones de uso aplicables a esas plataformas deben consultarse en la ficha del dataset.

## Procedimiento de obtención del recorte

1. Se descargó `cleaned_dataset.csv` desde Kaggle.
2. Se filtraron las filas de ocho artistas por **nombre exacto**: Oasis, Bon Jovi, Elton John, The Beatles, Mac Miller, Queen, Red Hot Chili Peppers y Pink Floyd (un filtro por texto parcial habría incluido también a "Queens of the Stone Age" e "Ivy Queen"). El dataset trae diez canciones de cada uno: 80 en total, conservadas en su orden original.
3. Se seleccionaron y renombraron nueve columnas (tabla siguiente) y se redondeó la duración a dos decimales.
4. Se generó `id_cancion` como código propio: prefijo del artista y número de orden dentro de su grupo (`OAS-001` a `OAS-010`, `QUE-001`, etc.).
5. Se guardó el mismo contenido en CSV y en JSON.

| Columna del recorte | Columna original | Transformación |
|---|---|---|
| `id_cancion` | — | Generada para este trabajo |
| `artista` | `Artist` | Ninguna |
| `cancion` | `Track` | Ninguna |
| `album` | `Album` | Ninguna |
| `tipo_album` | `Album_type` | Ninguna |
| `duracion_min` | `Duration_min` | Redondeada a 2 decimales |
| `streams` | `Stream` | Convertida a entero |
| `views` | `Views` | Convertida a entero |
| `likes` | `Likes` | Convertida a entero |
| `energy` | `Energy` | Ninguna |

## Archivos incluidos

- `canciones.csv`: catálogo base, 80 registros.
- `canciones.json`: el mismo catálogo en JSON (lista de objetos; los faltantes son `null`).
- `canciones_con_errores.csv` y `canciones_con_errores.json`: variante de prueba con 87 registros.

La variante de prueba conserva los 80 registros del catálogo en el mismo orden, con tres modificaciones para probar los datos opcionales y la normalización de espacios: `RHC-003` tiene `views` vacío, `RHC-010` tiene `likes` vacío y `QUE-001` tiene un espacio al final del nombre del artista. Además se agregaron siete registros de prueba (filas 81 a 87), creados copiando filas reales y alterando un solo campo. Su título lleva la marca `[PRUEBA]` (salvo el de título vacío) y no son datos de la fuente:

| Fila | `id_cancion` | Error introducido |
|---|---|---|
| 81 | `OAS-1` | Identificador mal formado |
| 82 | `RHC-001` | Identificador duplicado |
| 83 | `MMI-011` | `duracion_min` igual a 0 |
| 84 | `QUE-011` | `streams` negativo (-100) |
| 85 | `RHC-011` | `energy` fuera de rango (1.7) |
| 86 | `PFL-011` | `tipo_album` no permitido (`remix`) |
| 87 | `EJN-011` | `cancion` vacía |

## Unidad de análisis

Cada fila del CSV o cada objeto del JSON representa **una canción de un artista**. El recorte no pretende representar toda la música disponible en Spotify.

## Diccionario de variables

| Campo | Tipo | Descripción |
|---|---|---|
| `id_cancion` | Texto | Identificador interno con formato `AAA-NNN`. No es un identificador oficial de Spotify ni un ISRC. |
| `artista` | Texto | Nombre del intérprete o banda. |
| `cancion` | Texto | Título de la canción tal como figura en el dataset. |
| `album` | Texto | Nombre del álbum o lanzamiento tal como figura en el dataset. |
| `tipo_album` | Texto | `album`, `single` o `compilation`. |
| `duracion_min` | Decimal | Duración en minutos. Se acepta entre 0,5 y 30. |
| `streams` | Entero o faltante | Reproducciones en Spotify. No puede ser negativo; el valor 0 se interpreta como dato no disponible. |
| `views` | Entero o faltante | Visualizaciones del video asociado. No puede ser negativo. |
| `likes` | Entero o faltante | "Me gusta" del video asociado. No puede ser negativo. |
| `energy` | Decimal | Indicador de energía de la canción, entre 0 y 1. |

En CSV, los valores faltantes se representan con un campo vacío; en JSON, con `null`. Tras la normalización ambos se convierten en `None`.

## Criterios de limpieza

Las reglas de validación, el orden de rechazo y el tratamiento de los datos faltantes están descritos en la sección *Decisiones de limpieza* del [`README.md`](../README.md) principal. Dos puntos específicos de estos datos:

- **Ceros en `streams`.** En el catálogo base, 13 registros tienen `streams = 0` (nueve de las diez canciones de Pink Floyd, tres de Oasis y una de Queen). Se interpretan como dato no disponible: se convierten en `None` y cada cambio se registra en `outputs/ajustes.csv`. Es una suposición del trabajo, no un hecho demostrado sobre la fuente.
- **Espacios en textos.** Los textos se limpian de espacios sobrantes y el cambio queda registrado en `outputs/ajustes.csv`.

## Comprobaciones esperadas

| Archivo | Leídas | Aceptadas | Rechazadas | Ajustes registrados | Aceptadas con algún dato faltante |
|---|---:|---:|---:|---:|---:|
| `canciones.csv` / `canciones.json` | 80 | 80 | 0 | 13 | 13 |
| `canciones_con_errores.csv` / `canciones_con_errores.json` | 87 | 80 | 7 | 14 | 15 |

En el catálogo base, los 13 ajustes son los `streams = 0` convertidos a `None`. En la variante con errores hay un ajuste más (el texto normalizado de `QUE-001`) y dos faltantes más (`views` de `RHC-003` y `likes` de `RHC-010`), que se aceptan sin ajuste.

## Limitaciones

- La selección de ocho artistas y diez canciones por artista es acotada y no aleatoria; favorece a artistas muy conocidos y mayormente anglosajones.
- No se consultan datos en vivo: los valores corresponden al momento en que se publicó el dataset.
- Tratar los ceros de `streams` como faltantes puede afectar los totales y las comparaciones.
- Los nombres de álbum incluyen ediciones (`Deluxe`, `Remastered`), por lo que un mismo disco puede aparecer con nombres distintos y contarse por separado.
- El dataset combina métricas de plataformas distintas, y los archivos disponibles no explican cómo se vincularon `views` y `likes` con cada canción.
- Los registros de prueba de las variantes `*_con_errores` son sintéticos y no deben usarse para sacar conclusiones sobre música.

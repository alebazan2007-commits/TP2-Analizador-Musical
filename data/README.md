# Documentación de los Datos (`data/`)

## 1. Fuente, Responsable y Licencia
* **Fuente original:** Dataset *"Spotify dataset"* publicado en Kaggle (`https://www.kaggle.com/datasets/sanjanchaudhari/spotify-dataset`), archivo `cleaned_dataset.csv` (compuesto originalmente por 20.594 filas y 24 columnas).
* **Responsable:** `sanjanchaudhari` [AUTOR SEGÚN KAGGLE].
* **Licencia:** [COMPLETAR SEGÚN LA PÁGINA DEL DATASET] (Uso académico sobre metadatos públicos de canciones).
* **Fecha de consulta:** 2026-10-23 [FECHA].

---

## 2. Procedimiento de Construcción de los Archivos
1. **Selección de artistas (`canciones.csv` y `canciones.json`):** A partir de `cleaned_dataset.csv` se filtraron exactamente 8 artistas por nombre (`Oasis`, `Bon Jovi`, `Elton John`, `The Beatles`, `Mac Miller`, `Queen`, `Red Hot Chili Peppers` y `Pink Floyd`), conservando 10 canciones por cada uno (80 filas en total).
2. **Selección y transformación de variables:** Se seleccionaron y renombraron 9 columnas relevantes del dataset original, se redondeó `duracion_min` a 2 decimales y se generó la columna `id_cancion` como identificador propio con el formato `AAA-NNN` (prefijo de 3 letras del artista seguido de un número correlativo de 3 dígitos).
3. **Perturbaciones reales incluidas en las 80 filas base:** El conjunto incluye 2 filas reales con métricas `views` y `likes` vacías y 1 fila con espacio sobrante en el nombre del artista (`"Queen "`), además de 13 filas donde `streams` vale `0` en la fuente original.
4. **Archivos de prueba de validación (`canciones_con_errores.csv` y `canciones_con_errores.json`):** Contienen las 80 filas anteriores más 7 filas adicionales (filas 81 a 87), creadas como copias de filas reales con una única alteración deliberada cada una y marcadas con la etiqueta `"[PRUEBA]"` con el único propósito de demostrar el rechazo automático de datos inválidos.

---

## 3. Unidad de Análisis y Diccionario de Variables

* **Unidad de análisis:** Cada fila (en CSV) o cada objeto (en JSON) representa **una canción de un artista**.

| Columna | Tipo | Unidad / Rango | Descripción |
| :--- | :--- | :--- | :--- |
| `id_cancion` | Texto (`str`) | Formato `AAA-NNN` | Identificador único generado para el TP (`OAS`, `BJV`, `EJN`, `BTL`, `MMI`, `QUE`, `RHC`, `PFL` + correlativo). No proviene de Spotify. |
| `artista` | Texto (`str`) | Texto libre | Nombre del intérprete o banda musical. |
| `cancion` | Texto (`str`) | Texto libre | Título de la canción tal como figura en el catálogo. |
| `album` | Texto (`str`) | Texto libre | Nombre del álbum o lanzamiento al que pertenece la pista. |
| `tipo_album` | Texto (`str`) | `{album, single, compilation}` | Categoría del lanzamiento discográfico. |
| `duracion_min` | Decimal (`float`) | Minutos (`0.5` a `30.0`) | Duración de la canción en minutos decimales (redondeada a 2 decimales). |
| `streams` | Entero (`int`) | Reproducciones (`>= 0`) | Cantidad acumulada de reproducciones en Spotify (opcional; `0` equivale a dato no disponible). |
| `views` | Entero (`int`) | Vistas (`>= 0`) | Cantidad de visualizaciones asociadas a YouTube según el dataset original (opcional). |
| `likes` | Entero (`int`) | Me gusta (`>= 0`) | Cantidad de "me gusta" asociados a YouTube según el dataset original (opcional). |
| `energy` | Decimal (`float`) | Índice (`0.0` a `1.0`) | Indicador acústico de intensidad y actividad calculado por Spotify. |

---

## 4. Limitaciones y Sesgos Conocidos
1. **Muestra acotada y no representativa:** El recorte incluye únicamente 8 artistas consagrados, mayoritariamente de rock y pop anglosajón, por lo que las conclusiones no son generalizables a toda la plataforma Spotify.
2. **Significado de `streams = 0`:** En 13 de las 80 canciones (incluyendo 9 de las 10 canciones de Pink Floyd), la fuente registra `streams = 0`. Tratándose de canciones de alta difusión histórica, dicho cero representa un dato no disponible al momento de la captura original y es ajustado a `None` durante el procesamiento.
3. **Fragmentación por ediciones de álbumes:** Los nombres de álbum incluyen sufijos de edición (`Remastered`, `Deluxe Edition`, etc.), por lo que distintas reediciones de un mismo álbum pueden aparecer como álbumes separados al agrupar por nombre exacto.
4. **Origen de `views` y `likes`:** Son métricas de video asociadas a YouTube integradas en el dataset original de Kaggle, cuyo método exacto de emparejamiento depende del autor de la fuente.
5. **Carácter interno de `id_cancion`:** El código `AAA-NNN` es un identificador interno de cátedra y no constituye un código estándar de la industria (como ISRC o Spotify URI).
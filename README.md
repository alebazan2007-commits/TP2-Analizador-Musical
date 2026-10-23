# Analizador de Catálogo Musical de Rock y Pop Clásico (Spotify)

**Autor:** [TU NOMBRE]  
**Materia:** Programación Orientada a Datos — Trabajo Práctico 2 (Individual)  
**Carrera:** Licenciatura en Ciencia de Datos — Universidad Católica Argentina (UCA)

---

## 1. Problema, Usuario y Solución

* **Problema:** Quienes arman rankings, listas de reproducción o actividades didácticas sobre música suelen recibir catálogos en archivos CSV o JSON con errores de carga frecuentes: identificadores mal escritos o duplicados, duraciones nulas o fuera de escala, métricas negativas, valores de energía fuera de rango y datos faltantes. Auditar estos archivos y responder consultas a mano es lento, propenso a errores y no reproducible.
* **Usuario destinatario:** Aficionado a la música, curador de listas o docente que necesita validar un catálogo musical y realizar consultas agregadas y comparativas desde la consola de forma rápida y repetible.
* **Solución propuesta:** Aplicación de línea de comandos en Python 3.10+ (construida únicamente con la biblioteca estándar) que carga catálogos desde archivos CSV o JSON, normaliza los datos, valida reglas de esquema y de dominio registrando tanto las filas rechazadas como los ajustes aplicados, ejecuta 5 operaciones de análisis y exporta todos los resultados a archivos CSV en la carpeta `outputs/`.

---

## 2. Funcionalidades y Modo de Uso

La aplicación ofrece 5 operaciones principales mediante subcomandos de consola:

1. **`resumen`**: Calcula indicadores globales del catálogo (cantidad de canciones, artistas, álbumes distintos, conteo por tipo de álbum, duración media, energía media, total y promedio de reproducciones sobre canciones con dato disponible, y cantidad de canciones con datos faltantes).
2. **`filtrar`**: Filtra canciones combinando criterios opcionales (`--artista`, `--tipo-album`, `--dur-min`, `--dur-max`, `--streams-min`) sin distinguir mayúsculas ni minúsculas.
3. **`top`**: Genera el ranking de las `N` canciones con mayor cantidad de reproducciones (`streams`), con opción de filtrar por `--artista`.
4. **`albumes`**: Determina el álbum más escuchado de cada artista sumando los `streams` disponibles por álbum.
5. **`comparar`**: Compara mano a mano a dos artistas del catálogo (`--artista1` y `--artista2`) en cantidad de canciones, reproducciones totales y promedio, duración media y energía media, indicando quién lidera en cada métrica.

---

## 3. Fuente de Datos, Licencia y Unidad de Análisis

* **Fuente:** Dataset público *"Spotify dataset"* publicado por `sanjanchaudhari` en Kaggle (`https://www.kaggle.com/datasets/sanjanchaudhari/spotify-dataset`), a partir del archivo `cleaned_dataset.csv` (20.594 filas y 24 columnas).
* **Licencia:** Uso académico según los términos publicados en la página del dataset en Kaggle (metadatos factuales públicos; no incluye letras ni audio).
* **Unidad de análisis:** Cada fila u objeto representa **una canción de un artista** dentro del catálogo seleccionado (80 canciones reales distribuidas entre 8 artistas, a razón de 10 canciones por artista).

---

## 4. Instalación y Ejecución

### Requisitos
* **Python 3.10 o superior**.
* **Sin dependencias externas:** Se emplea exclusivamente la biblioteca estándar de Python (`csv`, `json`, `re`, `argparse`, `unittest`, `abc`, `os`, `sys`, `statistics`, `tempfile`).

### Comandos exactos para ejecutar la aplicación (desde la raíz del repositorio)

```bash
python -m src.main --entrada data/canciones.csv resumen
python -m src.main --entrada data/canciones.json filtrar --artista Queen --dur-min 3 --dur-max 6
python -m src.main --entrada data/canciones.csv top --n 5
python -m src.main --entrada data/canciones.csv albumes
python -m src.main --entrada data/canciones.json comparar --artista1 Queen --artista2 Oasis
python -m src.main --entrada data/canciones_con_errores.csv resumen

Comando exacto para ejecutar las pruebas unitarias
Bash

python -m unittest discover -s tests -t . -v

5. Organización del Código y Decisiones de Diseño
Plaintext

tp2-apellido/
├── README.md
├── requirements.txt
├── .gitignore
├── src/
│   ├── __init__.py
│   ├── fuentes.py
│   ├── pipeline.py
│   └── main.py
├── tests/
│   ├── __init__.py
│   └── test_app.py
├── data/
│   ├── README.md
│   ├── canciones.csv
│   ├── canciones.json
│   ├── canciones_con_errores.csv
│   └── canciones_con_errores.json
└── outputs/
    └── .gitkeep

    Jerarquía FuenteDatos (src/fuentes.py): Define la clase base abstracta FuenteDatos(ABC) con el método abstracto cargar(ruta) -> list[dict] y sus dos sublclases concretas FuenteCSV y FuenteJSON. La función fábrica obtener_fuente(ruta) selecciona la implementación según la extensión del archivo, desacoplando el formato físico del resto del flujo.

    Clase de dominio Cancion (src/pipeline.py): Representa una pista validada con sus 10 atributos y métodos propios del dominio (duracion_mmss(), streams_millones(), tiene_datos_faltantes(), a_dict()). No realiza lectura ni escritura de archivos.

    Funciones de responsabilidad única (src/pipeline.py): Cada etapa del procesamiento está separada en una función pura o acotada (normalizar_campos, validar_esquema, limpiar_datos, ejecutar_operacion, verificar_resultado, guardar_resultado, guardar_rechazos, guardar_ajustes).

    Expresión regular y validaciones complementarias: El formato sintáctico de id_cancion se valida con ^[A-Z]{3}-\d{3}$ (3 letras mayúsculas, guion y 3 dígitos). Como una expresión regular solo verifica el patrón de texto y no relaciones semánticas entre columnas ni contexto histórico, se complementa con un mapa de códigos por artista (OAS → Oasis, QUE → Queen, etc.) y un conjunto de IDs vistos para detectar duplicados.

6. Ejemplo de Resultado con Valores Reales

Al ejecutar python -m src.main --entrada data/canciones.csv resumen:

    Auditoría: 80 filas leídas, 80 aceptadas, 0 rechazadas y 13 ajustes registrados (streams=0 convertido a None).

    Resumen general:

        total_canciones: 80

        total_artistas: 8

        canciones_con_streams: 67

        streams_totales: 36387534829

        duracion_media_min: 4.34

        energy_media: 0.613

        canciones_con_faltantes: 15 (13 por streams ajustados a None + 2 por views/likes vacíos).

    Top 1 de reproducciones (top --n 1): QUE-003 — "Bohemian Rhapsody - Remastered 2011" (Queen) con 2038872787 streams.

    Álbum más escuchado por artista (albumes):

        Queen: "A Night At The Opera (Deluxe Remastered Version)" (2038872787 streams)

        Bon Jovi: "Slippery When Wet" (2276107852 streams)

        Red Hot Chili Peppers: "Californication (Deluxe Edition)" (2402351587 streams)

        Pink Floyd: "Wish You Were Here" (557368632 streams)

Al ejecutar sobre data/canciones_con_errores.csv:

    Se leen 87 filas, se aceptan 80 y se rechazan 7 (filas 81 a 87: OAS-1 por formato inválido, RHC-001 por ID duplicado, duración 0, streams -100, energy 1.7, tipo de álbum "remix" y nombre de canción vacío).

7. Decisiones de Limpieza y Normalización

    Normalización unificada CSV/JSON (normalizar_campos): Se aplican strip() y colapso de espacios múltiples internos en todas las cadenas (por ejemplo, "  Queen " pasa a "Queen"). Las cadenas vacías "" del CSV y los null del JSON se convierten a None. Los números se llevan a tipos nativos (int o float), aceptando representaciones enteras con .0 (ej. "100.0" → 100), pero preservando valores inválidos (como "12.5" en un campo entero o "abc") para que limpiar_datos los rechace con mensaje explícito.

    Orden determinista de rechazo (limpiar_datos): Cada fila inválida genera exactamente un registro de rechazo con el primer motivo detectado según el orden: (1) regex id_cancion, (2) correspondencia código-artista, (3) unicidad de id_cancion, (4) campos de texto obligatorios no vacíos, (5) tipo_album en {album, single, compilation}, (6) duracion_min en [0.5, 30.0], (7) streams, views y likes enteros >= 0 cuando están presentes, y (8) energy en [0.0, 1.0].

    Datos opcionales faltantes (views, likes, streams): Si views o likes vienen vacíos, la canción se acepta y quedan en None (nunca 0).

    Tratamiento de streams = 0 como dato faltante (Ajuste documentado): En el archivo original se detectaron 13 de 80 canciones (incluyendo 9 de las 10 de Pink Floyd) con streams = 0. Dado que se trata de éxitos mundiales donde 0 representa ausencia de registro en la captura original y no cero reproducciones reales, la aplicación convierte streams = 0 en None, acepta la canción y deja constancia auditable en la lista de ajustes (outputs/ajustes.csv). En cambio, un valor negativo como -100 constituye un error de integridad y se rechaza.

    Estructura de comparar_artistas: Para facilitar tanto la visualización tabular en consola como la exportación a CSV, comparar_artistas devuelve una lista de 3 diccionarios homogéneos: la primera fila corresponde a las métricas de artista1, la segunda a las de artista2 y la tercera fila (artista = "LÍDER") indica quién lidera en cada métrica (o "Empate").

8. Interpretación, Limitaciones y Alcance (v1)

    Interpretación y limitaciones: Los totales y promedios de streams se calculan únicamente sobre canciones con dato válido disponible (streams is not None). Como los nombres de álbum provienen de ediciones específicas de Spotify (por ejemplo, versiones Remastered o Deluxe), distintas ediciones de una misma obra se contabilizan según su nombre exacto en el catálogo.

    Alcance v1 y qué queda fuera: Esta versión cubre el flujo completo por consola con lectura CSV/JSON, limpieza auditada, 5 operaciones de consulta, verificación de invariantes y exportación a CSV. Quedan fuera del alcance interfaces web o gráficas, modelos de machine learning, consultas a APIs externas en vivo, análisis de letras o audio, bases de datos y generación de gráficos.

9. Identificación de la Versión Evaluada

La versión final entregada para evaluación se identifica en el repositorio Git mediante la etiqueta (tag) v1.0:
Bash

git tag v1.0
git show v1.0


### `requirements.txt`

```text
# Este proyecto utiliza exclusivamente la biblioteca estándar de Python 3.10+.
# No se requieren paquetes ni dependencias externas para ejecutar la aplicación ni los tests.
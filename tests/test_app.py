"""Suite de 28 pruebas unitarias para verificar fuentes, pipeline, dominio y CLI."""

import csv
import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import FrozenInstanceError
from typing import Any

from src.fuentes import FuenteCSV, FuenteJSON, obtener_fuente
from src.main import main
from src.pipeline import (
    COLUMNAS_ESPERADAS,
    Cancion,
    album_mas_escuchado_por_artista,
    comparar_artistas,
    ejecutar_operacion,
    filtrar_canciones,
    limpiar_datos,
    normalizar_campos,
    registrar_normalizaciones,
    resumen_general,
    top_canciones,
    validar_esquema,
    validar_formato_id,
    verificar_resultado,
)


def _crear_fila_prueba(**modificaciones: Any) -> dict[str, Any]:
    """Genera un diccionario con una fila base válida y permite sobreescribir campos."""
    fila: dict[str, Any] = {
        "id_cancion": "OAS-001",
        "artista": "Oasis",
        "cancion": "Wonderwall",
        "album": "(What's The Story) Morning Glory?",
        "tipo_album": "album",
        "duracion_min": 4.31,
        "streams": 1500000000,
        "views": 400000000,
        "likes": 3500000,
        "energy": 0.85,
    }
    fila.update(modificaciones)
    return fila


class TestAnalizadorMusical(unittest.TestCase):
    """Pruebas unitarias exhaustivas según las especificaciones de la cátedra."""

    def test_01_cancion_valida_metodos(self) -> None:
        """1. Cancion válida: duracion_mmss() de 5.5 = '5:30'; streams_millones() correcto."""
        cancion = Cancion(
            id_cancion="QUE-003",
            artista="Queen",
            cancion="Bohemian Rhapsody - Remastered 2011",
            album="A Night At The Opera (Deluxe Remastered Version)",
            tipo_album="album",
            duracion_min=5.5,
            streams=2038872787,
            views=1500000000,
            likes=10000000,
            energy=0.402,
        )
        self.assertEqual(cancion.duracion_mmss(), "5:30")
        self.assertEqual(cancion.streams_millones(), 2038.87)
        self.assertFalse(cancion.tiene_datos_faltantes())

    def test_02_cancion_con_streams_none(self) -> None:
        """2. Cancion con streams None: tiene_datos_faltantes() True y streams_millones() None."""
        cancion = Cancion(
            id_cancion="PFL-001",
            artista="Pink Floyd",
            cancion="Comfortably Numb",
            album="The Wall",
            tipo_album="album",
            duracion_min=6.37,
            streams=None,
            views=50000000,
            likes=500000,
            energy=0.4,
        )
        self.assertTrue(cancion.tiene_datos_faltantes())
        self.assertIsNone(cancion.streams_millones())

    def test_03_regex_id_cancion(self) -> None:
        """3. Regex id: válidos (OAS-001, RHC-010) e inválidos (OAS-1, oas-001, OAS001, OAS-0001, OA-001)."""
        self.assertTrue(validar_formato_id("OAS-001"))
        self.assertTrue(validar_formato_id("RHC-010"))

        for id_invalido in ("OAS-1", "oas-001", "OAS001", "OAS-0001", "OA-001"):
            self.assertFalse(
                validar_formato_id(id_invalido),
                f"Se esperaba inválido para '{id_invalido}'",
            )

    def test_04_codigo_id_no_corresponde_artista(self) -> None:
        """4. Código de id que no corresponde al artista (QUE-003 con artista Oasis) -> rechazo."""
        datos = normalizar_campos(
            [_crear_fila_prueba(id_cancion="QUE-003", artista="Oasis")]
        )
        canciones, rechazos, _ = limpiar_datos(datos)
        self.assertEqual(len(canciones), 0)
        self.assertEqual(len(rechazos), 1)
        self.assertIn("no corresponde al artista", rechazos[0]["motivo"])

    def test_05_duracion_limites_y_fuera_de_rango(self) -> None:
        """5. Duración: 0.5 y 30 aceptados; 0, -1, 0.49, 30.01 rechazados."""
        filas_validas = normalizar_campos(
            [
                _crear_fila_prueba(id_cancion="OAS-001", duracion_min=0.5),
                _crear_fila_prueba(id_cancion="OAS-002", duracion_min=30),
            ]
        )
        canciones_ok, rechazos_ok, _ = limpiar_datos(filas_validas)
        self.assertEqual(len(canciones_ok), 2)
        self.assertEqual(len(rechazos_ok), 0)

        filas_invalidas = normalizar_campos(
            [
                _crear_fila_prueba(id_cancion="OAS-003", duracion_min=0),
                _crear_fila_prueba(id_cancion="OAS-004", duracion_min=-1),
                _crear_fila_prueba(id_cancion="OAS-005", duracion_min=0.49),
                _crear_fila_prueba(id_cancion="OAS-006", duracion_min=30.01),
            ]
        )
        canciones_err, rechazos_err, _ = limpiar_datos(filas_invalidas)
        self.assertEqual(len(canciones_err), 0)
        self.assertEqual(len(rechazos_err), 4)

    def test_06_energy_limites_y_fuera_de_rango(self) -> None:
        """6. energy: 0.0 y 1.0 aceptados; -0.01 y 1.01 rechazados."""
        filas_validas = normalizar_campos(
            [
                _crear_fila_prueba(id_cancion="OAS-001", energy=0.0),
                _crear_fila_prueba(id_cancion="OAS-002", energy=1.0),
            ]
        )
        canciones_ok, rechazos_ok, _ = limpiar_datos(filas_validas)
        self.assertEqual(len(canciones_ok), 2)
        self.assertEqual(len(rechazos_ok), 0)

        filas_invalidas = normalizar_campos(
            [
                _crear_fila_prueba(id_cancion="OAS-003", energy=-0.01),
                _crear_fila_prueba(id_cancion="OAS-004", energy=1.01),
            ]
        )
        canciones_err, rechazos_err, _ = limpiar_datos(filas_invalidas)
        self.assertEqual(len(canciones_err), 0)
        self.assertEqual(len(rechazos_err), 2)

    def test_07_streams_ajuste_rechazo_y_vacio(self) -> None:
        """7. streams: 0 -> None con ajuste; -1 rechazado; 'abc' rechazado sin crash; vacío -> None."""
        filas = normalizar_campos(
            [
                _crear_fila_prueba(id_cancion="OAS-001", streams=0),
                _crear_fila_prueba(id_cancion="OAS-002", streams=-1),
                _crear_fila_prueba(id_cancion="OAS-003", streams="abc"),
                _crear_fila_prueba(id_cancion="OAS-004", streams=""),
            ]
        )
        canciones, rechazos, ajustes = limpiar_datos(filas)

        self.assertEqual(len(canciones), 2)
        self.assertIsNone(canciones[0].streams)
        self.assertIsNone(canciones[1].streams)
        self.assertEqual(len(ajustes), 1)
        self.assertEqual(ajustes[0]["id_cancion"], "OAS-001")
        self.assertEqual(ajustes[0]["valor_original"], 0)
        self.assertEqual(len(rechazos), 2)

    def test_08_id_duplicado(self) -> None:
        """8. ID duplicado: segunda aparición rechazada, primera aceptada."""
        filas = normalizar_campos(
            [
                _crear_fila_prueba(id_cancion="OAS-001", cancion="Primera"),
                _crear_fila_prueba(id_cancion="OAS-001", cancion="Segunda"),
            ]
        )
        canciones, rechazos, _ = limpiar_datos(filas)
        self.assertEqual(len(canciones), 1)
        self.assertEqual(canciones[0].cancion, "Primera")
        self.assertEqual(len(rechazos), 1)
        self.assertEqual(rechazos[0]["nro_fila"], 2)
        self.assertIn("duplicado", rechazos[0]["motivo"])

    def test_09_normalizacion_espacios_y_vacios(self) -> None:
        """9. Normalización: '  Queen ' -> 'Queen', espacios múltiples colapsados, '' -> None."""
        filas = normalizar_campos(
            [
                _crear_fila_prueba(
                    id_cancion="QUE-001",
                    artista="  Queen ",
                    cancion="Bohemian   Rhapsody  ",
                    views="",
                )
            ]
        )
        self.assertEqual(filas[0]["artista"], "Queen")
        self.assertEqual(filas[0]["cancion"], "Bohemian Rhapsody")
        self.assertIsNone(filas[0]["views"])

    def test_10_views_y_likes_vacios(self) -> None:
        """10. views/likes vacíos: aceptados con None, nunca 0."""
        filas = normalizar_campos(
            [_crear_fila_prueba(id_cancion="OAS-001", views="", likes=None)]
        )
        canciones, rechazos, _ = limpiar_datos(filas)
        self.assertEqual(len(rechazos), 0)
        self.assertEqual(len(canciones), 1)
        self.assertIsNone(canciones[0].views)
        self.assertIsNone(canciones[0].likes)
        self.assertTrue(canciones[0].tiene_datos_faltantes())

    def test_11_csv_vs_json_limpio_equivalentes(self) -> None:
        """11. CSV vs JSON (limpio): mismas 80 canciones (a_dict) en el mismo orden, mismos ajustes."""
        datos_csv = normalizar_campos(
            obtener_fuente("data/canciones.csv").cargar("data/canciones.csv")
        )
        datos_json = normalizar_campos(
            obtener_fuente("data/canciones.json").cargar("data/canciones.json")
        )

        canc_csv, rec_csv, aju_csv = limpiar_datos(datos_csv)
        canc_json, rec_json, aju_json = limpiar_datos(datos_json)

        self.assertEqual(len(canc_csv), 80)
        self.assertEqual(len(rec_csv), 0)
        self.assertEqual(len(aju_csv), 13)
        self.assertEqual([c.a_dict() for c in canc_csv], [c.a_dict() for c in canc_json])
        self.assertEqual(rec_csv, rec_json)
        self.assertEqual(aju_csv, aju_json)

    def test_12_csv_vs_json_con_errores_equivalentes(self) -> None:
        """12. CSV vs JSON (con errores): mismos 7 rechazos (nro_fila y motivo) y mismas 80 aceptadas."""
        datos_csv = normalizar_campos(
            obtener_fuente("data/canciones_con_errores.csv").cargar(
                "data/canciones_con_errores.csv"
            )
        )
        datos_json = normalizar_campos(
            obtener_fuente("data/canciones_con_errores.json").cargar(
                "data/canciones_con_errores.json"
            )
        )

        canc_csv, rec_csv, _ = limpiar_datos(datos_csv)
        canc_json, rec_json, _ = limpiar_datos(datos_json)

        self.assertEqual(len(datos_csv), 87)
        self.assertEqual(len(canc_csv), 80)
        self.assertEqual(len(rec_csv), 7)
        self.assertEqual([c.a_dict() for c in canc_csv], [c.a_dict() for c in canc_json])
        self.assertEqual(rec_csv, rec_json)

        filas_rechazadas = [r["nro_fila"] for r in rec_csv]
        self.assertEqual(filas_rechazadas, [81, 82, 83, 84, 85, 86, 87])

        faltantes = [c for c in canc_csv if c.tiene_datos_faltantes()]
        self.assertEqual(len(faltantes), 15)

    def test_13_conservacion_filas_en_los_cuatro_archivos(self) -> None:
        """13. Conservación: leídas = aceptadas + rechazadas en los cuatro archivos."""
        rutas = [
            "data/canciones.csv",
            "data/canciones.json",
            "data/canciones_con_errores.csv",
            "data/canciones_con_errores.json",
        ]
        for ruta in rutas:
            datos = normalizar_campos(obtener_fuente(ruta).cargar(ruta))
            canciones, rechazos, _ = limpiar_datos(datos)
            self.assertEqual(
                len(datos),
                len(canciones) + len(rechazos),
                f"Fallo de conservación en {ruta}",
            )

    def test_14_resumen_general_valores_conocidos(self) -> None:
        """14. resumen_general con los valores conocidos sobre data/canciones.csv."""
        datos = normalizar_campos(
            obtener_fuente("data/canciones.csv").cargar("data/canciones.csv")
        )
        canciones, _, _ = limpiar_datos(datos)
        resumen = resumen_general(canciones)

        self.assertEqual(resumen["total_canciones"], 80)
        self.assertEqual(resumen["total_artistas"], 8)
        self.assertEqual(resumen["canciones_con_streams"], 67)
        self.assertEqual(resumen["streams_totales"], 36387534829)
        self.assertEqual(resumen["duracion_media_min"], 4.34)
        self.assertEqual(resumen["energy_media"], 0.613)
        self.assertEqual(resumen["canciones_con_faltantes"], 13)

    def test_15_top_canciones_valores_conocidos_y_validaciones(self) -> None:
        """15. top_canciones: top 1 conocido; top 3 en orden descendente; n=0 -> error; sin None."""
        datos = normalizar_campos(
            obtener_fuente("data/canciones.csv").cargar("data/canciones.csv")
        )
        canciones, _, _ = limpiar_datos(datos)

        top1 = top_canciones(canciones, n=1)
        self.assertEqual(len(top1), 1)
        self.assertEqual(top1[0].id_cancion, "QUE-003")
        self.assertEqual(top1[0].cancion, "Bohemian Rhapsody - Remastered 2011")
        self.assertEqual(top1[0].streams, 2038872787)

        top3 = top_canciones(canciones, n=3)
        self.assertEqual(len(top3), 3)
        self.assertGreaterEqual(top3[0].streams, top3[1].streams)  # type: ignore[arg-type]
        self.assertGreaterEqual(top3[1].streams, top3[2].streams)  # type: ignore[arg-type]

        todos_top = top_canciones(canciones, n=100)
        self.assertEqual(len(todos_top), 67)
        self.assertTrue(all(c.streams is not None for c in todos_top))

        with self.assertRaises(ValueError):
            top_canciones(canciones, n=0)

    def test_16_album_mas_escuchado_por_artista_valores_conocidos(self) -> None:
        """16. album_mas_escuchado_por_artista con valores conocidos, 'sin datos' y verificación."""
        datos = normalizar_campos(
            obtener_fuente("data/canciones.csv").cargar("data/canciones.csv")
        )
        canciones, _, _ = limpiar_datos(datos)
        albumes = album_mas_escuchado_por_artista(canciones)
        verificar_resultado(albumes, canciones)

        mapa = {fila["artista"]: fila for fila in albumes}
        self.assertEqual(
            mapa["Queen"]["album"],
            "A Night At The Opera (Deluxe Remastered Version)",
        )
        self.assertEqual(mapa["Queen"]["streams_totales"], 2038872787)

        self.assertEqual(mapa["Bon Jovi"]["album"], "Slippery When Wet")
        self.assertEqual(mapa["Bon Jovi"]["streams_totales"], 2276107852)

        self.assertEqual(
            mapa["Red Hot Chili Peppers"]["album"],
            "Californication (Deluxe Edition)",
        )
        self.assertEqual(
            mapa["Red Hot Chili Peppers"]["streams_totales"], 2402351587
        )

        self.assertEqual(mapa["Pink Floyd"]["album"], "Wish You Were Here")
        self.assertEqual(mapa["Pink Floyd"]["streams_totales"], 557368632)

        # Caso de artista sin ningún dato de streams
        sin_streams = [
            Cancion("PFL-001", "Pink Floyd", "C1", "The Wall", "album", 4.0, None, 10, 1, 0.5)
        ]
        res_sin_datos = album_mas_escuchado_por_artista(sin_streams)
        self.assertEqual(res_sin_datos[0]["album"], "sin datos")
        self.assertEqual(res_sin_datos[0]["streams_totales"], "sin datos")

    def test_17_filtrar_canciones_casos(self) -> None:
        """17. filtrar: 'queen' -> 10; combinado; tipo_album 'single' -> 1; vacío; dur_min > dur_max -> error."""
        datos = normalizar_campos(
            obtener_fuente("data/canciones.csv").cargar("data/canciones.csv")
        )
        canciones, _, _ = limpiar_datos(datos)

        queen = filtrar_canciones(canciones, artista="queen")
        self.assertEqual(len(queen), 10)

        queen_dur = filtrar_canciones(
            canciones, artista="Queen", dur_min=3.0, dur_max=6.0
        )
        self.assertTrue(len(queen_dur) > 0)
        self.assertTrue(all(3.0 <= c.duracion_min <= 6.0 for c in queen_dur))

        singles = filtrar_canciones(canciones, tipo_album="single")
        self.assertEqual(len(singles), 1)

        vacio = filtrar_canciones(canciones, artista="Inexistente")
        self.assertEqual(vacio, [])

        with self.assertRaises(ValueError):
            filtrar_canciones(canciones, dur_min=10.0, dur_max=3.0)

    def test_18_comparar_artistas_casos(self) -> None:
        """18. comparar_artistas: Queen vs Oasis devuelve métricas; inexistente -> error; mismo -> error."""
        datos = normalizar_campos(
            obtener_fuente("data/canciones.csv").cargar("data/canciones.csv")
        )
        canciones, _, _ = limpiar_datos(datos)

        comp = comparar_artistas(canciones, "Queen", "Oasis")
        self.assertEqual(len(comp), 3)
        self.assertEqual(comp[0]["artista"], "Queen")
        self.assertEqual(comp[1]["artista"], "Oasis")
        self.assertEqual(comp[2]["artista"], "LÍDER")
        for clave in (
            "cantidad_canciones",
            "streams_totales",
            "streams_promedio",
            "duracion_media_min",
            "energy_media",
        ):
            self.assertIn(clave, comp[0])
            self.assertIn(clave, comp[1])
            self.assertIn(clave, comp[2])

        with self.assertRaises(ValueError):
            comparar_artistas(canciones, "Queen", "Artista Desconocido")

        with self.assertRaises(ValueError):
            comparar_artistas(canciones, "Queen", "queen")

    def test_19_fuentes_errores_explicitos(self) -> None:
        """19. Fuentes: inexistente, vacío, JSON mal formado, JSON no lista, extensión .txt -> error."""
        with self.assertRaises(ValueError):
            obtener_fuente("archivo.txt")

        with self.assertRaises(FileNotFoundError):
            obtener_fuente("no_existe.csv").cargar("no_existe.csv")

        with tempfile.TemporaryDirectory() as tmpdir:
            vacio_csv = os.path.join(tmpdir, "vacio.csv")
            with open(vacio_csv, "w", encoding="utf-8"):
                pass
            with self.assertRaises(ValueError):
                obtener_fuente(vacio_csv).cargar(vacio_csv)

            mal_json = os.path.join(tmpdir, "mal.json")
            with open(mal_json, "w", encoding="utf-8") as f:
                f.write("{json_roto:")
            with self.assertRaises(ValueError):
                obtener_fuente(mal_json).cargar(mal_json)

            no_lista_json = os.path.join(tmpdir, "objeto.json")
            with open(no_lista_json, "w", encoding="utf-8") as f:
                f.write('{"id_cancion": "OAS-001"}')
            with self.assertRaises(ValueError):
                obtener_fuente(no_lista_json).cargar(no_lista_json)

    def test_20_esquema_columna_faltante(self) -> None:
        """20. Esquema: falta una columna -> error que nombra la columna."""
        fila_incompleta = _crear_fila_prueba()
        del fila_incompleta["energy"]

        with self.assertRaises(ValueError) as ctx:
            validar_esquema([fila_incompleta])
        self.assertIn("energy", str(ctx.exception))

    def test_21_determinismo(self) -> None:
        """21. Determinismo: dos ejecuciones con la misma entrada dan resultados idénticos."""
        datos1 = normalizar_campos(
            obtener_fuente("data/canciones.csv").cargar("data/canciones.csv")
        )
        c1, r1, a1 = limpiar_datos(datos1)
        res1 = ejecutar_operacion(c1, "albumes")

        datos2 = normalizar_campos(
            obtener_fuente("data/canciones.csv").cargar("data/canciones.csv")
        )
        c2, r2, a2 = limpiar_datos(datos2)
        res2 = ejecutar_operacion(c2, "albumes")

        self.assertEqual([x.a_dict() for x in c1], [x.a_dict() for x in c2])
        self.assertEqual(r1, r2)
        self.assertEqual(a1, a2)
        self.assertEqual(res1, res2)

    def test_22_main_cli_codigos_salida(self) -> None:
        """22. main(): resumen sobre data/canciones.csv devuelve 0; archivo inexistente devuelve != 0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            buf_out = io.StringIO()
            with redirect_stdout(buf_out):
                codigo_ok = main(
                    [
                        "--entrada",
                        "data/canciones.csv",
                        "--salida-dir",
                        tmpdir,
                        "resumen",
                    ]
                )
            self.assertEqual(codigo_ok, 0)
            self.assertTrue(os.path.exists(os.path.join(tmpdir, "resultado_resumen.csv")))
            self.assertTrue(os.path.exists(os.path.join(tmpdir, "rechazos.csv")))
            self.assertTrue(os.path.exists(os.path.join(tmpdir, "ajustes.csv")))

            buf_err = io.StringIO()
            with redirect_stderr(buf_err):
                codigo_err = main(
                    [
                        "--entrada",
                        "data/archivo_inexistente.csv",
                        "--salida-dir",
                        tmpdir,
                        "resumen",
                    ]
                )
            self.assertNotEqual(codigo_err, 0)


    def test_23_bom_de_excel_se_lee_bien(self) -> None:
        """23. CSV y JSON guardados con BOM (como hace Excel en Windows) se leen igual que sin BOM."""
        with tempfile.TemporaryDirectory() as tmpdir:
            for nombre, fuente in (("canciones.csv", FuenteCSV()), ("canciones.json", FuenteJSON())):
                with open(f"data/{nombre}", encoding="utf-8") as origen:
                    contenido = origen.read()
                ruta_bom = os.path.join(tmpdir, nombre)
                with open(ruta_bom, "w", encoding="utf-8-sig", newline="") as destino:
                    destino.write(contenido)

                filas_bom = fuente.cargar(ruta_bom)
                self.assertEqual(filas_bom, fuente.cargar(f"data/{nombre}"))
                self.assertIn("id_cancion", filas_bom[0])
                validar_esquema(normalizar_campos(filas_bom))  # no debe lanzar error

    def test_24_regex_id_rechaza_salto_de_linea_final(self) -> None:
        """24. La regex usa fullmatch: 'OAS-001' pasa; 'OAS-001\\n' y 'OAS-001 ' no."""
        self.assertTrue(validar_formato_id("OAS-001"))
        self.assertFalse(validar_formato_id("OAS-001\n"))
        self.assertFalse(validar_formato_id("OAS-001 "))

    def test_25_normalizaciones_quedan_registradas(self) -> None:
        """25. El espacio sobrante de 'Queen ' (fila 61) se registra; el catálogo base no tiene ninguno."""
        resultados = {}
        for ruta in ("data/canciones_con_errores.csv", "data/canciones_con_errores.json"):
            originales = obtener_fuente(ruta).cargar(ruta)
            resultados[ruta] = registrar_normalizaciones(originales, normalizar_campos(originales))

        csv_ajustes, json_ajustes = resultados.values()
        self.assertEqual(csv_ajustes, json_ajustes)
        self.assertEqual(len(csv_ajustes), 1)
        self.assertEqual(csv_ajustes[0]["nro_fila"], 61)
        self.assertEqual(csv_ajustes[0]["id_cancion"], "QUE-001")
        self.assertEqual(csv_ajustes[0]["campo"], "artista")
        self.assertEqual(csv_ajustes[0]["valor_original"], "Queen ")

        base = obtener_fuente("data/canciones.csv").cargar("data/canciones.csv")
        self.assertEqual(registrar_normalizaciones(base, normalizar_campos(base)), [])
        self.assertEqual(
            registrar_normalizaciones(
                obtener_fuente("data/canciones_con_errores.csv").cargar("data/canciones_con_errores.csv"),
                normalizar_campos(
                    obtener_fuente("data/canciones_con_errores.csv").cargar("data/canciones_con_errores.csv")
                ),
                filas_excluidas={61},
            ),
            [],
        )

    def test_26_verificar_resultado_detecta_resultados_incorrectos(self) -> None:
        """26. verificar_resultado acepta resultados correctos y rechaza top desordenado o álbum que no es el máximo."""
        datos = normalizar_campos(obtener_fuente("data/canciones.csv").cargar("data/canciones.csv"))
        canciones, _, _ = limpiar_datos(datos)

        top = top_canciones(canciones, n=3)
        verificar_resultado(top, canciones, "top")
        with self.assertRaises(ValueError):
            verificar_resultado(list(reversed(top)), canciones, "top")

        albumes = album_mas_escuchado_por_artista(canciones)
        verificar_resultado(albumes, canciones, "albumes")

        fila_queen = next(f for f in albumes if f["artista"] == "Queen")
        otro_album = next(
            c.album for c in canciones
            if c.artista == "Queen" and c.streams and c.album != fila_queen["album"]
        )
        suma_otro = sum(c.streams for c in canciones if c.album == otro_album and c.streams)
        mala = [dict(f) for f in albumes]
        for fila in mala:
            if fila["artista"] == "Queen":
                fila["album"], fila["streams_totales"] = otro_album, suma_otro
        with self.assertRaises(ValueError):
            verificar_resultado(mala, canciones, "albumes")  # suma correcta, pero no es el máximo

        falsa = [dict(f) for f in albumes]
        for fila in falsa:
            if fila["artista"] == "Oasis":
                fila["album"], fila["streams_totales"] = "sin datos", "sin datos"
        with self.assertRaises(ValueError):
            verificar_resultado(falsa, canciones, "albumes")  # Oasis sí tiene streams

    def test_27_cancion_es_inmutable_y_comparable(self) -> None:
        """27. Cancion (dataclass frozen): igual si sus campos son iguales, hasheable y no modificable."""
        args = ("QUE-003", "Queen", "Bohemian Rhapsody", "A Night At The Opera", "album", 5.9, 10, 1, 1, 0.4)
        c1, c2 = Cancion(*args), Cancion(*args)
        self.assertEqual(c1, c2)
        self.assertEqual(hash(c1), hash(c2))
        self.assertEqual(list(c1.a_dict().keys()), COLUMNAS_ESPERADAS)
        with self.assertRaises(FrozenInstanceError):
            c1.streams = 99  # type: ignore[misc]

    def test_28_main_exporta_normalizaciones_en_ajustes_csv(self) -> None:
        """28. main() sobre el archivo con errores deja 14 ajustes (13 streams=0 + 1 texto) en ajustes.csv."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with redirect_stdout(io.StringIO()):
                codigo = main(
                    ["--entrada", "data/canciones_con_errores.csv", "--salida-dir", tmpdir, "resumen"]
                )
            self.assertEqual(codigo, 0)
            with open(os.path.join(tmpdir, "ajustes.csv"), encoding="utf-8", newline="") as f:
                filas = list(csv.DictReader(f))
            self.assertEqual(len(filas), 14)
            self.assertEqual(sum(1 for fila in filas if fila["campo"] == "streams"), 13)
            self.assertEqual([fila["id_cancion"] for fila in filas if fila["campo"] == "artista"], ["QUE-001"])

            with open(os.path.join(tmpdir, "rechazos.csv"), encoding="utf-8", newline="") as f:
                self.assertEqual(len(list(csv.DictReader(f))), 7)


if __name__ == "__main__":
    unittest.main()
"""Interfaz de línea de comandos (CLI) para el analizador de catálogo musical."""

import argparse
import os
import sys
from typing import Any

from src.fuentes import obtener_fuente
from src.pipeline import (
    Cancion,
    ejecutar_operacion,
    guardar_ajustes,
    guardar_rechazos,
    guardar_resultado,
    limpiar_datos,
    normalizar_campos,
    validar_esquema,
    verificar_resultado,
)


def construir_parser() -> argparse.ArgumentParser:
    """Construye y configura el parser de argumentos con sus 5 subcomandos."""
    parser = argparse.ArgumentParser(
        prog="python -m src.main",
        description="Analizador de catálogo musical de rock y pop clásico (Spotify).",
    )
    parser.add_argument(
        "--entrada",
        default="data/canciones.csv",
        help="Ruta al archivo de datos de entrada (.csv o .json). Por defecto: data/canciones.csv",
    )
    parser.add_argument(
        "--salida-dir",
        dest="salida_dir",
        default="outputs",
        help="Directorio donde se exportarán los archivos CSV. Por defecto: outputs",
    )

    subparsers = parser.add_subparsers(
        dest="operacion", help="Operación de análisis a realizar"
    )

    # 1. Subcomando resumen
    subparsers.add_parser("resumen", help="Muestra el resumen general del catálogo.")

    # 2. Subcomando filtrar
    parser_filtrar = subparsers.add_parser(
        "filtrar", help="Filtra canciones según criterios combinables."
    )
    parser_filtrar.add_argument("--artista", type=str, default=None, help="Nombre del artista.")
    parser_filtrar.add_argument(
        "--tipo-album",
        dest="tipo_album",
        type=str,
        default=None,
        help="Tipo de álbum (album, single, compilation).",
    )
    parser_filtrar.add_argument(
        "--dur-min",
        dest="dur_min",
        type=float,
        default=None,
        help="Duración mínima en minutos.",
    )
    parser_filtrar.add_argument(
        "--dur-max",
        dest="dur_max",
        type=float,
        default=None,
        help="Duración máxima en minutos.",
    )
    parser_filtrar.add_argument(
        "--streams-min",
        dest="streams_min",
        type=int,
        default=None,
        help="Cantidad mínima de streams.",
    )

    # 3. Subcomando top
    parser_top = subparsers.add_parser(
        "top", help="Muestra el ranking de canciones con más streams."
    )
    parser_top.add_argument(
        "--n", type=int, default=5, help="Cantidad de canciones a listar (por defecto: 5)."
    )
    parser_top.add_argument(
        "--artista", type=str, default=None, help="Filtrar el ranking por artista."
    )

    # 4. Subcomando albumes
    subparsers.add_parser(
        "albumes", help="Obtiene el álbum más escuchado por cada artista."
    )

    # 5. Subcomando comparar
    parser_comparar = subparsers.add_parser(
        "comparar", help="Compara las métricas de dos artistas del catálogo."
    )
    parser_comparar.add_argument(
        "--artista1", required=True, type=str, help="Nombre del primer artista."
    )
    parser_comparar.add_argument(
        "--artista2", required=True, type=str, help="Nombre del segundo artista."
    )

    return parser


def _formatear_tabla(filas: list[dict[str, Any]]) -> str:
    """Da formato a una lista de diccionarios como una tabla de texto alineada."""
    if not filas:
        return "No se encontraron canciones"

    columnas = list(filas[0].keys())
    anchos: dict[str, int] = {}
    for col in columnas:
        ancho_max_valor = max(
            len(str(fila.get(col) if fila.get(col) is not None else "N/D"))
            for fila in filas
        )
        anchos[col] = max(len(col), ancho_max_valor)

    encabezado = " | ".join(col.ljust(anchos[col]) for col in columnas)
    separador = "-" * len(encabezado)
    lineas = [encabezado, separador]

    for fila in filas:
        celdas = [
            str(fila.get(col) if fila.get(col) is not None else "N/D").ljust(anchos[col])
            for col in columnas
        ]
        lineas.append(" | ".join(celdas))

    return "\n".join(lineas)


def _imprimir_reporte(
    ruta_entrada: str,
    total_leidas: int,
    canciones: list[Cancion],
    rechazos: list[dict[str, Any]],
    ajustes: list[dict[str, Any]],
    operacion: str,
    resultado: dict[str, Any] | list[Any],
) -> None:
    """Muestra en salida estándar la auditoría de limpieza y la tabla de resultados."""
    print("=" * 78)
    print(f"AUDITORÍA DE PROCESAMIENTO — Fuente: {ruta_entrada}")
    print("=" * 78)
    print(f"Filas leídas     : {total_leidas}")
    print(f"Filas aceptadas  : {len(canciones)}")
    print(f"Filas rechazadas : {len(rechazos)}")
    print(f"Filas ajustadas  : {len(ajustes)}")

    if rechazos:
        print("\nDetalle de filas rechazadas:")
        for rec in rechazos:
            print(
                f"  - Fila {rec['nro_fila']} (ID: {rec['id_cancion']}): {rec['motivo']}"
            )

    if ajustes:
        print("\nDetalle de filas ajustadas:")
        for aj in ajustes:
            print(
                f"  - Fila {aj['nro_fila']} (ID: {aj['id_cancion']}): "
                f"{aj['campo']}={aj['valor_original']} -> {aj['accion']}"
            )

    print("\n" + "=" * 78)
    print(f"RESULTADO DE LA OPERACIÓN: {operacion.upper()}")
    print("=" * 78)

    if isinstance(resultado, dict):
        fila_mostrar = {
            k: (
                f"album={v['album']}, single={v['single']}, compilation={v['compilation']}"
                if isinstance(v, dict)
                else v
            )
            for k, v in resultado.items()
        }
        print(_formatear_tabla([fila_mostrar]))
    elif isinstance(resultado, list):
        if not resultado:
            print("No se encontraron canciones")
        elif isinstance(resultado[0], Cancion):
            print(_formatear_tabla([c.a_dict() for c in resultado]))
        else:
            print(_formatear_tabla(resultado))


def main(argv: list[str] | None = None) -> int:
    """Ejecuta el flujo principal de la aplicación y devuelve el código de salida."""
    parser = construir_parser()
    args = parser.parse_args(argv)

    if not args.operacion:
        parser.print_help()
        return 1

    try:
        ruta_entrada = args.entrada
        salida_dir = args.salida_dir

        parametros: dict[str, Any] = {
            "artista": getattr(args, "artista", None),
            "tipo_album": getattr(args, "tipo_album", None),
            "dur_min": getattr(args, "dur_min", None),
            "dur_max": getattr(args, "dur_max", None),
            "streams_min": getattr(args, "streams_min", None),
            "n": getattr(args, "n", 5),
            "artista1": getattr(args, "artista1", None),
            "artista2": getattr(args, "artista2", None),
        }

        datos = obtener_fuente(ruta_entrada).cargar(ruta_entrada)
        total_leidas = len(datos)
        datos = normalizar_campos(datos)
        validar_esquema(datos)
        canciones, rechazos, ajustes = limpiar_datos(datos)
        resultado = ejecutar_operacion(canciones, args.operacion, parametros)
        verificar_resultado(resultado, canciones)

        ruta_salida = os.path.join(salida_dir, f"resultado_{args.operacion}.csv")
        ruta_rechazos = os.path.join(salida_dir, "rechazos.csv")
        ruta_ajustes = os.path.join(salida_dir, "ajustes.csv")

        guardar_resultado(resultado, ruta_salida)
        guardar_rechazos(rechazos, ruta_rechazos)
        guardar_ajustes(ajustes, ruta_ajustes)

        _imprimir_reporte(
            ruta_entrada=ruta_entrada,
            total_leidas=total_leidas,
            canciones=canciones,
            rechazos=rechazos,
            ajustes=ajustes,
            operacion=args.operacion,
            resultado=resultado,
        )
        print(
            f"\nSalidas exportadas en: '{ruta_salida}', '{ruta_rechazos}' y '{ruta_ajustes}'."
        )
        return 0

    except (FileNotFoundError, ValueError, OSError) as err:
        print(f"Error: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
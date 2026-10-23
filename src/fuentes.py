"""Módulo de lectura de fuentes de datos en formatos CSV y JSON."""

from abc import ABC, abstractmethod
import csv
import json
import os
from typing import Any


class FuenteDatos(ABC):
    """Clase base abstracta para lectores de fuentes de datos tabulares."""

    @abstractmethod
    def cargar(self, ruta: str) -> list[dict[str, Any]]:
        """Carga los registros desde la ruta indicada y devuelve una lista de diccionarios."""


class FuenteCSV(FuenteDatos):
    """Implementación de lectura para archivos CSV codificados en UTF-8."""

    def cargar(self, ruta: str) -> list[dict[str, Any]]:
        """Lee un archivo CSV y retorna sus filas como una lista de diccionarios."""
        if not os.path.exists(ruta):
            raise FileNotFoundError(f"No existe el archivo solicitado: '{ruta}'.")
        if os.path.getsize(ruta) == 0:
            raise ValueError(f"El archivo CSV está vacío: '{ruta}'.")

        with open(ruta, mode="r", encoding="utf-8", newline="") as archivo:
            lector = csv.DictReader(archivo)
            if not lector.fieldnames:
                raise ValueError(
                    f"El archivo CSV no posee encabezados válidos: '{ruta}'."
                )
            filas = [dict(fila) for fila in lector]

        if not filas:
            raise ValueError(
                f"El archivo CSV no contiene filas de datos: '{ruta}'."
            )
        return filas


class FuenteJSON(FuenteDatos):
    """Implementación de lectura para archivos JSON codificados en UTF-8."""

    def cargar(self, ruta: str) -> list[dict[str, Any]]:
        """Lee un archivo JSON validando que su estructura sea una lista de objetos."""
        if not os.path.exists(ruta):
            raise FileNotFoundError(f"No existe el archivo solicitado: '{ruta}'.")
        if os.path.getsize(ruta) == 0:
            raise ValueError(f"El archivo JSON está vacío: '{ruta}'.")

        try:
            with open(ruta, mode="r", encoding="utf-8") as archivo:
                contenido = json.load(archivo)
        except json.JSONDecodeError as err:
            raise ValueError(
                f"El archivo JSON está mal formado ('{ruta}'): {err.msg}."
            ) from err

        if not isinstance(contenido, list):
            raise ValueError(
                f"El archivo JSON '{ruta}' debe contener una lista de objetos en su raíz."
            )
        if not contenido:
            raise ValueError(f"La lista del archivo JSON está vacía: '{ruta}'.")
        if not all(isinstance(elemento, dict) for elemento in contenido):
            raise ValueError(
                f"Todos los elementos del archivo JSON '{ruta}' deben ser objetos (diccionarios)."
            )

        return [dict(elemento) for elemento in contenido]


def obtener_fuente(ruta: str) -> FuenteDatos:
    """Devuelve la instancia de FuenteDatos correspondiente según la extensión del archivo."""
    _, extension = os.path.splitext(ruta.lower())
    if extension == ".csv":
        return FuenteCSV()
    if extension == ".json":
        return FuenteJSON()
    raise ValueError(
        f"Extensión de archivo no soportada ('{extension}'). Utilice '.csv' o '.json'."
    )
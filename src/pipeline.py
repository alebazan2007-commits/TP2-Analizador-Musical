"""Módulo de dominio, normalización, validación, operaciones y exportación."""

import csv
import os
import re
import statistics
from typing import Any

COLUMNAS_ESPERADAS: list[str] = [
    "id_cancion",
    "artista",
    "cancion",
    "album",
    "tipo_album",
    "duracion_min",
    "streams",
    "views",
    "likes",
    "energy",
]

CODIGOS_ARTISTA: dict[str, str] = {
    "OAS": "Oasis",
    "BJV": "Bon Jovi",
    "EJN": "Elton John",
    "BTL": "The Beatles",
    "MMI": "Mac Miller",
    "QUE": "Queen",
    "RHC": "Red Hot Chili Peppers",
    "PFL": "Pink Floyd",
}

TIPOS_ALBUM_PERMITIDOS: set[str] = {"album", "single", "compilation"}

# Expresión regular para id_cancion: 3 letras mayúsculas, guion y 3 dígitos (ej: OAS-001)
PATRON_ID_CANCION: re.Pattern[str] = re.compile(r"^[A-Z]{3}-\d{3}$")


class Cancion:
    """Representa una canción validada del catálogo musical."""

    def __init__(
        self,
        id_cancion: str,
        artista: str,
        cancion: str,
        album: str,
        tipo_album: str,
        duracion_min: float,
        streams: int | None,
        views: int | None,
        likes: int | None,
        energy: float,
    ) -> None:
        self.id_cancion: str = id_cancion
        self.artista: str = artista
        self.cancion: str = cancion
        self.album: str = album
        self.tipo_album: str = tipo_album
        self.duracion_min: float = duracion_min
        self.streams: int | None = streams
        self.views: int | None = views
        self.likes: int | None = likes
        self.energy: float = energy

    def duracion_mmss(self) -> str:
        """Formatea la duración en minutos decimales como 'M:SS' (ej: 5.5 -> '5:30')."""
        total_segundos = round(self.duracion_min * 60)
        minutos = total_segundos // 60
        segundos = total_segundos % 60
        return f"{minutos}:{segundos:02d}"

    def streams_millones(self) -> float | None:
        """Devuelve los streams expresados en millones redondeados a 2 decimales, o None."""
        if self.streams is None:
            return None
        return round(self.streams / 1_000_000, 2)

    def tiene_datos_faltantes(self) -> bool:
        """Retorna True si alguno de los campos opcionales (streams, views o likes) es None."""
        return (
            self.streams is None
            or self.views is None
            or self.likes is None
        )

    def a_dict(self) -> dict[str, Any]:
        """Convierte la canción en un diccionario respetando el orden oficial de columnas."""
        return {
            "id_cancion": self.id_cancion,
            "artista": self.artista,
            "cancion": self.cancion,
            "album": self.album,
            "tipo_album": self.tipo_album,
            "duracion_min": self.duracion_min,
            "streams": self.streams,
            "views": self.views,
            "likes": self.likes,
            "energy": self.energy,
        }

    def __eq__(self, otro: object) -> bool:
        """Compara dos instancias de Cancion por igualdad exacta de sus atributos."""
        if not isinstance(otro, Cancion):
            return False
        return self.a_dict() == otro.a_dict()


class ListaTopCanciones(list[Cancion]):
    """Subclase de lista que identifica resultados provenientes de top_canciones."""


def validar_formato_id(id_cancion: Any) -> bool:
    """Comprueba mediante regex si id_cancion respeta el patrón 'AAA-NNN'.

    Valida únicamente la estructura sintáctica: 3 letras mayúsculas de prefijo,
    un guion medio y 3 dígitos numéricos (ej: 'OAS-001').
    NO comprueba que el código de artista coincida con la columna 'artista',
    ni que el identificador exista en un catálogo externo o sea único.
    """
    if not isinstance(id_cancion, str):
        return False
    return bool(PATRON_ID_CANCION.match(id_cancion))


def _normalizar_texto(valor: Any) -> str | None:
    """Elimina espacios extremos, colapsa espacios múltiples y convierte '' en None."""
    if valor is None:
        return None
    limpio = " ".join(str(valor).strip().split())
    return limpio if limpio != "" else None


def _normalizar_entero(valor: Any) -> Any:
    """Normaliza un valor numérico entero proveniente de CSV o JSON.

    Acepta enteros con o sin '.0' (ej: '100', '100.0', 100, 100.0 -> 100).
    Si el valor tiene parte fraccionaria no nula (ej: '12.5') o texto no numérico,
    lo conserva como cadena/valor inválido para que limpiar_datos lo rechace.
    """
    if isinstance(valor, bool):
        return str(valor)
    if isinstance(valor, int):
        return valor
    if isinstance(valor, float):
        return int(valor) if valor.is_integer() else str(valor)

    texto = _normalizar_texto(valor)
    if texto is None:
        return None
    try:
        numero = float(texto)
        if numero.is_integer():
            return int(numero)
        return texto
    except ValueError:
        return texto


def _normalizar_decimal(valor: Any) -> Any:
    """Normaliza un valor decimal proveniente de CSV o JSON a float si es posible."""
    if isinstance(valor, bool):
        return str(valor)
    if isinstance(valor, (int, float)):
        return float(valor)

    texto = _normalizar_texto(valor)
    if texto is None:
        return None
    try:
        return float(texto)
    except ValueError:
        return texto


def normalizar_campos(datos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Unifica la representación interna de filas provenientes de CSV o JSON."""
    campos_texto = {"id_cancion", "artista", "cancion", "album", "tipo_album"}
    campos_enteros = {"streams", "views", "likes"}
    campos_decimales = {"duracion_min", "energy"}

    normalizados: list[dict[str, Any]] = []
    for fila in datos:
        nueva_fila: dict[str, Any] = {}
        for clave, valor in fila.items():
            clave_limpia = (
                " ".join(clave.strip().split())
                if isinstance(clave, str)
                else clave
            )
            if clave_limpia in campos_texto:
                nueva_fila[clave_limpia] = _normalizar_texto(valor)
            elif clave_limpia in campos_enteros:
                nueva_fila[clave_limpia] = _normalizar_entero(valor)
            elif clave_limpia in campos_decimales:
                nueva_fila[clave_limpia] = _normalizar_decimal(valor)
            else:
                nueva_fila[clave_limpia] = _normalizar_texto(valor)
        normalizados.append(nueva_fila)

    return normalizados


def validar_esquema(datos: list[dict[str, Any]]) -> None:
    """Verifica que todas las filas contengan las 10 columnas obligatorias del esquema."""
    if not datos:
        raise ValueError("No hay datos cargados para validar el esquema.")

    for nro_fila, fila in enumerate(datos, start=1):
        for columna in COLUMNAS_ESPERADAS:
            if columna not in fila:
                raise ValueError(
                    f"Error de esquema en la fila {nro_fila}: falta la columna '{columna}'."
                )


def _convertir_entero_estricto(valor: Any) -> int:
    """Convierte un valor normalizado a int o lanza ValueError si no es entero."""
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise ValueError(f"Valor no entero: '{valor}'")
    return valor


def _convertir_decimal_estricto(valor: Any) -> float:
    """Convierte un valor normalizado a float o lanza ValueError si no es numérico."""
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise ValueError(f"Valor no numérico: '{valor}'")
    return float(valor)


def limpiar_datos(
    datos: list[dict[str, Any]],
) -> tuple[list[Cancion], list[dict[str, Any]], list[dict[str, Any]]]:
    """Valida las reglas de negocio registrando rechazos y ajustes con su motivo."""
    canciones: list[Cancion] = []
    rechazos: list[dict[str, Any]] = []
    ajustes: list[dict[str, Any]] = []
    ids_vistos: set[str] = set()

    for nro_fila, fila in enumerate(datos, start=1):
        id_raw = fila.get("id_cancion")
        id_etiqueta = str(id_raw) if id_raw is not None else "SIN_ID"

        # 1. Formato de id_cancion mediante expresión regular
        if not validar_formato_id(id_raw):
            rechazos.append(
                {
                    "nro_fila": nro_fila,
                    "id_cancion": id_etiqueta,
                    "motivo": f"id_cancion con formato inválido: '{id_etiqueta}'. Se esperaba 'AAA-NNN'.",
                }
            )
            continue

        id_cancion = str(id_raw)
        prefijo = id_cancion.split("-")[0]
        artista_raw = fila.get("artista")

        # 2. Correspondencia entre código del ID y nombre del artista
        artista_esperado = CODIGOS_ARTISTA.get(prefijo)
        if artista_esperado is None or (
            artista_raw is not None and artista_raw != artista_esperado
        ):
            rechazos.append(
                {
                    "nro_fila": nro_fila,
                    "id_cancion": id_cancion,
                    "motivo": (
                        f"El prefijo '{prefijo}' de id_cancion no corresponde "
                        f"al artista '{artista_raw}' (esperado: '{artista_esperado}')."
                    ),
                }
            )
            continue

        # 3. Unicidad de id_cancion
        if id_cancion in ids_vistos:
            rechazos.append(
                {
                    "nro_fila": nro_fila,
                    "id_cancion": id_cancion,
                    "motivo": f"id_cancion duplicado: '{id_cancion}'.",
                }
            )
            continue

        # 4. Campos de texto obligatorios (artista, cancion, album) no vacíos
        campo_vacio = None
        for campo_texto in ("artista", "cancion", "album"):
            if fila.get(campo_texto) is None or str(fila.get(campo_texto)).strip() == "":
                campo_vacio = campo_texto
                break
        if campo_vacio is not None:
            rechazos.append(
                {
                    "nro_fila": nro_fila,
                    "id_cancion": id_cancion,
                    "motivo": f"El campo obligatorio '{campo_vacio}' está vacío.",
                }
            )
            continue

        artista = str(fila["artista"])
        nombre_cancion = str(fila["cancion"])
        album = str(fila["album"])

        # 5. tipo_album dentro de {album, single, compilation}
        tipo_album_raw = fila.get("tipo_album")
        if tipo_album_raw is None or str(tipo_album_raw) not in TIPOS_ALBUM_PERMITIDOS:
            rechazos.append(
                {
                    "nro_fila": nro_fila,
                    "id_cancion": id_cancion,
                    "motivo": (
                        f"tipo_album inválido: '{tipo_album_raw}'. "
                        "Valores permitidos: album, single, compilation."
                    ),
                }
            )
            continue
        tipo_album = str(tipo_album_raw)

        # 6. duracion_min numérica y dentro de [0.5, 30.0]
        try:
            duracion_min = _convertir_decimal_estricto(fila.get("duracion_min"))
        except ValueError:
            rechazos.append(
                {
                    "nro_fila": nro_fila,
                    "id_cancion": id_cancion,
                    "motivo": f"duracion_min no numérica: '{fila.get('duracion_min')}'.",
                }
            )
            continue

        if not (0.5 <= duracion_min <= 30.0):
            rechazos.append(
                {
                    "nro_fila": nro_fila,
                    "id_cancion": id_cancion,
                    "motivo": f"duracion_min fuera de rango [0.5, 30.0]: {duracion_min}.",
                }
            )
            continue

        # 7. streams, views, likes: si existen deben ser enteros >= 0
        enteros_validados: dict[str, int | None] = {}
        error_entero: str | None = None
        for campo_ent in ("streams", "views", "likes"):
            valor_ent = fila.get(campo_ent)
            if valor_ent is None:
                enteros_validados[campo_ent] = None
            else:
                try:
                    numero_ent = _convertir_entero_estricto(valor_ent)
                except ValueError:
                    error_entero = f"El campo '{campo_ent}' no es un entero válido: '{valor_ent}'."
                    break
                if numero_ent < 0:
                    error_entero = (
                        f"El campo '{campo_ent}' no puede ser negativo: {numero_ent}."
                    )
                    break
                enteros_validados[campo_ent] = numero_ent

        if error_entero is not None:
            rechazos.append(
                {
                    "nro_fila": nro_fila,
                    "id_cancion": id_cancion,
                    "motivo": error_entero,
                }
            )
            continue

        # 8. energy numérica y dentro de [0.0, 1.0]
        try:
            energy = _convertir_decimal_estricto(fila.get("energy"))
        except ValueError:
            rechazos.append(
                {
                    "nro_fila": nro_fila,
                    "id_cancion": id_cancion,
                    "motivo": f"energy no numérica: '{fila.get('energy')}'.",
                }
            )
            continue

        if not (0.0 <= energy <= 1.0):
            rechazos.append(
                {
                    "nro_fila": nro_fila,
                    "id_cancion": id_cancion,
                    "motivo": f"energy fuera de rango [0.0, 1.0]: {energy}.",
                }
            )
            continue

        # Decisión de limpieza: streams = 0 significa "dato no disponible" -> None + ajuste
        streams_final = enteros_validados["streams"]
        if streams_final == 0:
            streams_final = None
            ajustes.append(
                {
                    "nro_fila": nro_fila,
                    "id_cancion": id_cancion,
                    "campo": "streams",
                    "valor_original": 0,
                    "accion": "Convertido a None (streams=0 indica dato no disponible)",
                }
            )

        ids_vistos.add(id_cancion)
        canciones.append(
            Cancion(
                id_cancion=id_cancion,
                artista=artista,
                cancion=nombre_cancion,
                album=album,
                tipo_album=tipo_album,
                duracion_min=duracion_min,
                streams=streams_final,
                views=enteros_validados["views"],
                likes=enteros_validados["likes"],
                energy=energy,
            )
        )

    return canciones, rechazos, ajustes


def resumen_general(canciones: list[Cancion]) -> dict[str, Any]:
    """Calcula las métricas globales sobre la lista de canciones válidas."""
    if not canciones:
        return {
            "total_canciones": 0,
            "total_artistas": 0,
            "total_albumes": 0,
            "conteo_tipo_album": {"album": 0, "single": 0, "compilation": 0},
            "tipo_album_album": 0,
            "tipo_album_single": 0,
            "tipo_album_compilation": 0,
            "duracion_media_min": 0.0,
            "energy_media": 0.0,
            "canciones_con_streams": 0,
            "streams_totales": 0,
            "streams_promedio": 0.0,
            "canciones_con_faltantes": 0,
        }

    artistas = {c.artista for c in canciones}
    albumes = {c.album for c in canciones}
    conteo_tipos = {
        "album": sum(1 for c in canciones if c.tipo_album == "album"),
        "single": sum(1 for c in canciones if c.tipo_album == "single"),
        "compilation": sum(1 for c in canciones if c.tipo_album == "compilation"),
    }

    duracion_media = round(statistics.mean(c.duracion_min for c in canciones), 2)
    energy_media = round(statistics.mean(c.energy for c in canciones), 3)

    con_streams = [c.streams for c in canciones if c.streams is not None]
    streams_totales = sum(con_streams) if con_streams else 0
    streams_promedio = (
        round(statistics.mean(con_streams), 2) if con_streams else 0.0
    )
    faltantes = sum(1 for c in canciones if c.tiene_datos_faltantes())

    return {
        "total_canciones": len(canciones),
        "total_artistas": len(artistas),
        "total_albumes": len(albumes),
        "conteo_tipo_album": conteo_tipos,
        "tipo_album_album": conteo_tipos["album"],
        "tipo_album_single": conteo_tipos["single"],
        "tipo_album_compilation": conteo_tipos["compilation"],
        "duracion_media_min": duracion_media,
        "energy_media": energy_media,
        "canciones_con_streams": len(con_streams),
        "streams_totales": streams_totales,
        "streams_promedio": streams_promedio,
        "canciones_con_faltantes": faltantes,
    }


def filtrar_canciones(
    canciones: list[Cancion],
    artista: str | None = None,
    tipo_album: str | None = None,
    dur_min: float | None = None,
    dur_max: float | None = None,
    streams_min: int | None = None,
) -> list[Cancion]:
    """Filtra canciones combinando artista, tipo de álbum, duración y streams mínimos."""
    if dur_min is not None and dur_max is not None and dur_min > dur_max:
        raise ValueError(
            f"Rango de duración inválido: dur_min ({dur_min}) no puede ser mayor que dur_max ({dur_max})."
        )

    artista_norm = artista.strip().lower() if artista is not None else None
    tipo_norm = tipo_album.strip().lower() if tipo_album is not None else None

    filtradas: list[Cancion] = []
    for cancion in canciones:
        if artista_norm is not None and cancion.artista.lower() != artista_norm:
            continue
        if tipo_norm is not None and cancion.tipo_album.lower() != tipo_norm:
            continue
        if dur_min is not None and cancion.duracion_min < dur_min:
            continue
        if dur_max is not None and cancion.duracion_min > dur_max:
            continue
        if streams_min is not None:
            if cancion.streams is None or cancion.streams < streams_min:
                continue
        filtradas.append(cancion)

    return filtradas


def top_canciones(
    canciones: list[Cancion], n: int = 5, artista: str | None = None
) -> list[Cancion]:
    """Devuelve las N canciones con más streams (descendente, desempate por canción ascendente)."""
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ValueError("El parámetro 'n' debe ser un número entero mayor o igual a 1.")

    candidatas = canciones
    if artista is not None:
        artista_norm = artista.strip().lower()
        candidatas = [c for c in candidatas if c.artista.lower() == artista_norm]

    con_streams = [c for c in candidatas if c.streams is not None]
    ordenadas = sorted(
        con_streams,
        key=lambda c: (-int(c.streams), c.cancion.lower(), c.id_cancion),  # type: ignore[arg-type]
    )
    return ListaTopCanciones(ordenadas[:n])


def album_mas_escuchado_por_artista(
    canciones: list[Cancion],
) -> list[dict[str, Any]]:
    """Determina el álbum con mayor suma de streams para cada artista del catálogo."""
    por_artista: dict[str, list[Cancion]] = {}
    for cancion in canciones:
        por_artista.setdefault(cancion.artista, []).append(cancion)

    resultado: list[dict[str, Any]] = []
    for artista in sorted(por_artista.keys()):
        pistas_artista = por_artista[artista]
        pistas_con_streams = [c for c in pistas_artista if c.streams is not None]

        if not pistas_con_streams:
            resultado.append(
                {
                    "artista": artista,
                    "album": "sin datos",
                    "streams_totales": "sin datos",
                    "canciones_con_streams": 0,
                }
            )
            continue

        streams_por_album: dict[str, int] = {}
        conteo_por_album: dict[str, int] = {}
        for pista in pistas_con_streams:
            assert pista.streams is not None
            streams_por_album[pista.album] = (
                streams_por_album.get(pista.album, 0) + pista.streams
            )
            conteo_por_album[pista.album] = (
                conteo_por_album.get(pista.album, 0) + 1
            )

        album_ganador = min(
            streams_por_album.keys(),
            key=lambda nom_alb: (-streams_por_album[nom_alb], nom_alb),
        )
        resultado.append(
            {
                "artista": artista,
                "album": album_ganador,
                "streams_totales": streams_por_album[album_ganador],
                "canciones_con_streams": conteo_por_album[album_ganador],
            }
        )

    return resultado


def _determinar_lider(
    nombre1: str, valor1: float | int, nombre2: str, valor2: float | int
) -> str:
    """Devuelve el nombre del artista con mayor valor en una métrica o 'Empate'."""
    if valor1 > valor2:
        return nombre1
    if valor2 > valor1:
        return nombre2
    return "Empate"


def comparar_artistas(
    canciones: list[Cancion], artista1: str, artista2: str
) -> list[dict[str, Any]]:
    """Compara dos artistas en métricas clave e indica quién lidera en cada una."""
    disponibles_mapa: dict[str, str] = {c.artista.lower(): c.artista for c in canciones}
    lista_disponibles = ", ".join(sorted(disponibles_mapa.values()))

    norm1 = artista1.strip().lower() if artista1 else ""
    norm2 = artista2.strip().lower() if artista2 else ""

    if norm1 not in disponibles_mapa:
        raise ValueError(
            f"El artista '{artista1}' no existe en el catálogo. Artistas disponibles: {lista_disponibles}."
        )
    if norm2 not in disponibles_mapa:
        raise ValueError(
            f"El artista '{artista2}' no existe en el catálogo. Artistas disponibles: {lista_disponibles}."
        )
    if norm1 == norm2:
        raise ValueError(
            f"No se puede comparar a un artista consigo mismo ('{disponibles_mapa[norm1]}')."
        )

    real1 = disponibles_mapa[norm1]
    real2 = disponibles_mapa[norm2]

    def _calcular_metricas(nombre_real: str) -> dict[str, Any]:
        pistas = [c for c in canciones if c.artista == nombre_real]
        con_str = [c.streams for c in pistas if c.streams is not None]
        streams_tot = sum(con_str) if con_str else 0
        streams_prom = round(statistics.mean(con_str), 2) if con_str else 0.0
        dur_media = round(statistics.mean(c.duracion_min for c in pistas), 2)
        eng_media = round(statistics.mean(c.energy for c in pistas), 3)
        return {
            "artista": nombre_real,
            "cantidad_canciones": len(pistas),
            "canciones_con_streams": len(con_str),
            "streams_totales": streams_tot,
            "streams_promedio": streams_prom,
            "duracion_media_min": dur_media,
            "energy_media": eng_media,
        }

    m1 = _calcular_metricas(real1)
    m2 = _calcular_metricas(real2)

    fila_lider: dict[str, Any] = {
        "artista": "LÍDER",
        "cantidad_canciones": _determinar_lider(
            real1, m1["cantidad_canciones"], real2, m2["cantidad_canciones"]
        ),
        "canciones_con_streams": _determinar_lider(
            real1, m1["canciones_con_streams"], real2, m2["canciones_con_streams"]
        ),
        "streams_totales": _determinar_lider(
            real1, m1["streams_totales"], real2, m2["streams_totales"]
        ),
        "streams_promedio": _determinar_lider(
            real1, m1["streams_promedio"], real2, m2["streams_promedio"]
        ),
        "duracion_media_min": _determinar_lider(
            real1, m1["duracion_media_min"], real2, m2["duracion_media_min"]
        ),
        "energy_media": _determinar_lider(
            real1, m1["energy_media"], real2, m2["energy_media"]
        ),
    }

    return [m1, m2, fila_lider]


def ejecutar_operacion(
    canciones: list[Cancion],
    operacion: str,
    parametros: dict[str, Any] | None = None,
) -> dict[str, Any] | list[Any]:
    """Despacha y ejecuta la operación solicitada sobre el catálogo limpio."""
    params = parametros or {}
    if operacion == "resumen":
        return resumen_general(canciones)
    if operacion == "filtrar":
        return filtrar_canciones(
            canciones,
            artista=params.get("artista"),
            tipo_album=params.get("tipo_album"),
            dur_min=params.get("dur_min"),
            dur_max=params.get("dur_max"),
            streams_min=params.get("streams_min"),
        )
    if operacion == "top":
        n_val = params.get("n", 5)
        return top_canciones(
            canciones,
            n=5 if n_val is None else n_val,
            artista=params.get("artista"),
        )
    if operacion == "albumes":
        return album_mas_escuchado_por_artista(canciones)
    if operacion == "comparar":
        return comparar_artistas(
            canciones,
            artista1=str(params.get("artista1", "")),
            artista2=str(params.get("artista2", "")),
        )
    raise ValueError(f"Operación no reconocida: '{operacion}'.")


def verificar_resultado(
    resultado: dict[str, Any] | list[Any], canciones: list[Cancion]
) -> None:
    """Verifica invariantes de consistencia sobre las canciones y el resultado."""
    for cancion in canciones:
        if cancion.duracion_min < 0.5 or cancion.duracion_min > 30.0:
            raise ValueError("Invariante violado: canción con duración fuera de rango.")
        if cancion.streams is not None and cancion.streams <= 0:
            raise ValueError(
                "Invariante violado: canción aceptada con streams negativos o cero sin ajustar."
            )
        if cancion.views is not None and cancion.views < 0:
            raise ValueError("Invariante violado: views negativo.")
        if cancion.likes is not None and cancion.likes < 0:
            raise ValueError("Invariante violado: likes negativo.")
        if cancion.energy < 0.0 or cancion.energy > 1.0:
            raise ValueError("Invariante violado: energy fuera de [0.0, 1.0].")

    # Propiedad: la suma de streams agrupada por álbum coincide con la suma total de canciones con streams
    total_streams_directo = sum(
        c.streams for c in canciones if c.streams is not None
    )
    streams_por_artista_album: dict[tuple[str, str], int] = {}
    for cancion in canciones:
        if cancion.streams is not None:
            clave = (cancion.artista, cancion.album)
            streams_por_artista_album[clave] = (
                streams_por_artista_album.get(clave, 0) + cancion.streams
            )

    if sum(streams_por_artista_album.values()) != total_streams_directo:
        raise ValueError(
            "Inconsistencia interna: la suma de streams por álbum no coincide con el total general."
        )

    if isinstance(resultado, dict):
        if resultado.get("total_canciones", 0) < 0 or resultado.get("streams_totales", 0) < 0:
            raise ValueError("Invariante violado: valores negativos en el resumen general.")
        if resultado.get("streams_totales", 0) != total_streams_directo:
            raise ValueError(
                "Inconsistencia en resumen: streams_totales no coincide con la suma de las canciones."
            )

    elif isinstance(resultado, ListaTopCanciones):
        for idx, cancion in enumerate(resultado):
            if cancion.streams is None or cancion.streams < 0:
                raise ValueError(
                    "Invariante violado en top: incluye una canción sin streams válidos."
                )
            if idx > 0:
                anterior = resultado[idx - 1]
                assert anterior.streams is not None
                if cancion.streams > anterior.streams:
                    raise ValueError(
                        "Invariante violado en top: la lista no está ordenada de forma descendente."
                    )

    elif isinstance(resultado, list) and resultado:
        primero = resultado[0]
        if isinstance(primero, dict) and "album" in primero and "streams_totales" in primero:
            for fila in resultado:
                st = fila["streams_totales"]
                if st != "sin datos":
                    if int(st) < 0:
                        raise ValueError("Invariante violado: streams_totales negativo en álbumes.")
                    esperado = streams_por_artista_album.get(
                        (fila["artista"], fila["album"]), 0
                    )
                    if int(st) != esperado:
                        raise ValueError(
                            f"La suma de streams del álbum '{fila['album']}' ({st}) no coincide con el cálculo ({esperado})."
                        )


def guardar_resultado(
    resultado: dict[str, Any] | list[Any], ruta_salida: str
) -> None:
    """Guarda el resultado de una operación en formato CSV codificado en UTF-8."""
    directorio = os.path.dirname(ruta_salida)
    if directorio:
        os.makedirs(directorio, exist_ok=True)

    with open(ruta_salida, mode="w", encoding="utf-8", newline="") as archivo:
        if isinstance(resultado, dict):
            fila_plana = {
                k: (
                    f"album={v['album']};single={v['single']};compilation={v['compilation']}"
                    if isinstance(v, dict)
                    else v
                )
                for k, v in resultado.items()
            }
            campos = list(fila_plana.keys())
            escritor = csv.DictWriter(archivo, fieldnames=campos)
            escritor.writeheader()
            escritor.writerow(fila_plana)
        elif isinstance(resultado, list):
            if not resultado:
                escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS_ESPERADAS)
                escritor.writeheader()
            elif isinstance(resultado[0], Cancion):
                escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS_ESPERADAS)
                escritor.writeheader()
                for cancion in resultado:
                    escritor.writerow(cancion.a_dict())
            elif isinstance(resultado[0], dict):
                campos = list(resultado[0].keys())
                escritor = csv.DictWriter(archivo, fieldnames=campos)
                escritor.writeheader()
                for item in resultado:
                    escritor.writerow(item)


def guardar_rechazos(
    rechazos: list[dict[str, Any]], ruta_rechazos: str
) -> None:
    """Exporta las filas rechazadas ordenadas por nro_fila a un archivo CSV."""
    directorio = os.path.dirname(ruta_rechazos)
    if directorio:
        os.makedirs(directorio, exist_ok=True)

    campos = ["nro_fila", "id_cancion", "motivo"]
    with open(ruta_rechazos, mode="w", encoding="utf-8", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=campos)
        escritor.writeheader()
        for rechazo in sorted(rechazos, key=lambda r: int(r["nro_fila"])):
            escritor.writerow(
                {
                    "nro_fila": rechazo["nro_fila"],
                    "id_cancion": rechazo["id_cancion"],
                    "motivo": rechazo["motivo"],
                }
            )


def guardar_ajustes(
    ajustes: list[dict[str, Any]], ruta_ajustes: str
) -> None:
    """Exporta el registro de filas ajustadas ordenadas por nro_fila a un archivo CSV."""
    directorio = os.path.dirname(ruta_ajustes)
    if directorio:
        os.makedirs(directorio, exist_ok=True)

    campos = ["nro_fila", "id_cancion", "campo", "valor_original", "accion"]
    with open(ruta_ajustes, mode="w", encoding="utf-8", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=campos)
        escritor.writeheader()
        for ajuste in sorted(ajustes, key=lambda a: int(a["nro_fila"])):
            escritor.writerow(
                {
                    "nro_fila": ajuste["nro_fila"],
                    "id_cancion": ajuste["id_cancion"],
                    "campo": ajuste["campo"],
                    "valor_original": ajuste["valor_original"],
                    "accion": ajuste["accion"],
                }
            )
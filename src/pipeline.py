"""Módulo de dominio, normalización, validación, operaciones y exportación."""

import csv
import os
import re
import statistics
from dataclasses import asdict, dataclass, replace
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

DURACION_MIN_PERMITIDA: float = 0.5
DURACION_MAX_PERMITIDA: float = 30.0
ENERGY_MIN_PERMITIDA: float = 0.0
ENERGY_MAX_PERMITIDA: float = 1.0
CAMPOS_TEXTO: tuple[str, ...] = ("id_cancion", "artista", "cancion", "album", "tipo_album")

# Expresión regular para id_cancion: 3 letras mayúsculas, guion y 3 dígitos (ej: OAS-001).
# Se aplica con fullmatch (todo el texto debe coincidir); con match + '$' un
# identificador con salto de línea final ("OAS-001\n") pasaría la validación.
PATRON_ID_CANCION: re.Pattern[str] = re.compile(r"[A-Z]{3}-\d{3}")


@dataclass(frozen=True)
class Cancion:
    """Canción validada del catálogo musical.

    Es un dataclass inmutable (frozen): una vez que la fila pasó la limpieza, sus
    valores no deberían cambiar. Python genera __init__, __eq__ y __hash__ a partir
    de los campos. streams, views y likes son opcionales (None = dato no disponible).
    """

    id_cancion: str
    artista: str
    cancion: str
    album: str
    tipo_album: str
    duracion_min: float
    streams: int | None
    views: int | None
    likes: int | None
    energy: float

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
        return self.streams is None or self.views is None or self.likes is None

    def a_dict(self) -> dict[str, Any]:
        """Convierte la canción en un diccionario respetando el orden oficial de columnas."""
        return asdict(self)


def validar_formato_id(id_cancion: Any) -> bool:
    """Comprueba mediante regex si id_cancion respeta el patrón 'AAA-NNN'.

    Valida únicamente la estructura sintáctica: 3 letras mayúsculas de prefijo,
    un guion medio y 3 dígitos numéricos (ej: 'OAS-001').
    NO comprueba que el código de artista coincida con la columna 'artista',
    ni que el identificador exista en un catálogo externo o sea único.
    """
    if not isinstance(id_cancion, str):
        return False
    return bool(PATRON_ID_CANCION.fullmatch(id_cancion))


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


def _etiqueta_id(fila: dict[str, Any]) -> str:
    """Devuelve el id de la fila como texto para los informes ('SIN_ID' si falta)."""
    id_raw = fila.get("id_cancion")
    return str(id_raw) if id_raw is not None else "SIN_ID"


def _motivo_identificador(fila: dict[str, Any], ids_vistos: set[str]) -> str | None:
    """Reglas 1 a 3: formato del id (regex), prefijo coherente con el artista y unicidad."""
    id_raw = fila.get("id_cancion")
    if not validar_formato_id(id_raw):
        return f"id_cancion con formato inválido: '{_etiqueta_id(fila)}'. Se esperaba 'AAA-NNN'."

    id_cancion = str(id_raw)
    prefijo = id_cancion.split("-")[0]
    artista_raw = fila.get("artista")
    artista_esperado = CODIGOS_ARTISTA.get(prefijo)
    if artista_esperado is None or (
        artista_raw is not None and artista_raw != artista_esperado
    ):
        return (
            f"El prefijo '{prefijo}' de id_cancion no corresponde "
            f"al artista '{artista_raw}' (esperado: '{artista_esperado}')."
        )
    if id_cancion in ids_vistos:
        return f"id_cancion duplicado: '{id_cancion}'."
    return None


def _motivo_textos(fila: dict[str, Any]) -> str | None:
    """Reglas 4 y 5: textos obligatorios no vacíos y tipo_album permitido."""
    for campo in ("artista", "cancion", "album"):
        valor = fila.get(campo)
        if valor is None or str(valor).strip() == "":
            return f"El campo obligatorio '{campo}' está vacío."

    tipo_album = fila.get("tipo_album")
    if tipo_album is None or str(tipo_album) not in TIPOS_ALBUM_PERMITIDOS:
        return (
            f"tipo_album inválido: '{tipo_album}'. "
            "Valores permitidos: album, single, compilation."
        )
    return None


def _leer_duracion(fila: dict[str, Any]) -> tuple[float | None, str | None]:
    """Regla 6: duracion_min numérica y dentro del rango. Devuelve (valor, motivo)."""
    try:
        duracion = _convertir_decimal_estricto(fila.get("duracion_min"))
    except ValueError:
        return None, f"duracion_min no numérica: '{fila.get('duracion_min')}'."
    if not (DURACION_MIN_PERMITIDA <= duracion <= DURACION_MAX_PERMITIDA):
        return None, (
            f"duracion_min fuera de rango "
            f"[{DURACION_MIN_PERMITIDA}, {DURACION_MAX_PERMITIDA}]: {duracion}."
        )
    return duracion, None


def _leer_enteros(
    fila: dict[str, Any],
) -> tuple[dict[str, int | None] | None, str | None]:
    """Regla 7: streams, views y likes, si existen, deben ser enteros >= 0."""
    valores: dict[str, int | None] = {}
    for campo in ("streams", "views", "likes"):
        valor = fila.get(campo)
        if valor is None:
            valores[campo] = None
            continue
        try:
            numero = _convertir_entero_estricto(valor)
        except ValueError:
            return None, f"El campo '{campo}' no es un entero válido: '{valor}'."
        if numero < 0:
            return None, f"El campo '{campo}' no puede ser negativo: {numero}."
        valores[campo] = numero
    return valores, None


def _leer_energy(fila: dict[str, Any]) -> tuple[float | None, str | None]:
    """Regla 8: energy numérica y dentro de [0.0, 1.0]."""
    try:
        energy = _convertir_decimal_estricto(fila.get("energy"))
    except ValueError:
        return None, f"energy no numérica: '{fila.get('energy')}'."
    if not (ENERGY_MIN_PERMITIDA <= energy <= ENERGY_MAX_PERMITIDA):
        return None, (
            f"energy fuera de rango "
            f"[{ENERGY_MIN_PERMITIDA}, {ENERGY_MAX_PERMITIDA}]: {energy}."
        )
    return energy, None


def _validar_fila(
    fila: dict[str, Any], ids_vistos: set[str]
) -> tuple[Cancion | None, str | None]:
    """Aplica las 8 reglas de rechazo en orden y se detiene en la primera que falla.

    Devuelve (Cancion, None) si la fila es válida o (None, motivo) si se rechaza.
    """
    motivo = _motivo_identificador(fila, ids_vistos) or _motivo_textos(fila)
    if motivo is not None:
        return None, motivo

    duracion, motivo = _leer_duracion(fila)
    if motivo is not None:
        return None, motivo

    enteros, motivo = _leer_enteros(fila)
    if motivo is not None:
        return None, motivo

    energy, motivo = _leer_energy(fila)
    if motivo is not None:
        return None, motivo

    return Cancion(
        id_cancion=str(fila["id_cancion"]),
        artista=str(fila["artista"]),
        cancion=str(fila["cancion"]),
        album=str(fila["album"]),
        tipo_album=str(fila["tipo_album"]),
        duracion_min=duracion,  # type: ignore[arg-type]
        streams=enteros["streams"],  # type: ignore[index]
        views=enteros["views"],  # type: ignore[index]
        likes=enteros["likes"],  # type: ignore[index]
        energy=energy,  # type: ignore[arg-type]
    ), None


def _aplicar_ajuste_streams_cero(
    cancion: Cancion, nro_fila: int
) -> tuple[Cancion, dict[str, Any] | None]:
    """Decisión de limpieza: streams = 0 significa "dato no disponible" -> None.

    Devuelve la canción (corregida si hizo falta) y el registro del ajuste, o None
    si no hubo cambio. Un streams negativo no llega acá: ya fue rechazado.
    """
    if cancion.streams != 0:
        return cancion, None
    ajuste = {
        "nro_fila": nro_fila,
        "id_cancion": cancion.id_cancion,
        "campo": "streams",
        "valor_original": 0,
        "accion": "Convertido a None (streams=0 indica dato no disponible)",
    }
    return replace(cancion, streams=None), ajuste


def limpiar_datos(
    datos: list[dict[str, Any]],
) -> tuple[list[Cancion], list[dict[str, Any]], list[dict[str, Any]]]:
    """Separa las filas en canciones válidas, rechazos y ajustes, cada uno con su motivo.

    nro_fila cuenta desde 1 en el archivo de datos. Un rechazo por fila, con el
    primer motivo encontrado (ver _validar_fila).
    """
    canciones: list[Cancion] = []
    rechazos: list[dict[str, Any]] = []
    ajustes: list[dict[str, Any]] = []
    ids_vistos: set[str] = set()

    for nro_fila, fila in enumerate(datos, start=1):
        cancion, motivo = _validar_fila(fila, ids_vistos)
        if cancion is None:
            rechazos.append(
                {"nro_fila": nro_fila, "id_cancion": _etiqueta_id(fila), "motivo": motivo}
            )
            continue

        cancion, ajuste = _aplicar_ajuste_streams_cero(cancion, nro_fila)
        if ajuste is not None:
            ajustes.append(ajuste)
        ids_vistos.add(cancion.id_cancion)
        canciones.append(cancion)

    return canciones, rechazos, ajustes


def registrar_normalizaciones(
    originales: list[dict[str, Any]],
    normalizados: list[dict[str, Any]],
    filas_excluidas: set[int] | None = None,
) -> list[dict[str, Any]]:
    """Registra las filas cuyo texto cambió al normalizar (espacios sobrantes).

    Compara cada campo de texto antes y después de normalizar_campos. No cuenta el
    paso de "" a None: eso es un dato faltante, no un cambio de texto. filas_excluidas
    permite omitir las filas rechazadas, que no llegan al catálogo.
    """
    excluidas = filas_excluidas or set()
    ajustes: list[dict[str, Any]] = []
    for nro_fila, (antes, despues) in enumerate(zip(originales, normalizados), start=1):
        if nro_fila in excluidas:
            continue
        for campo in CAMPOS_TEXTO:
            original = antes.get(campo)
            normal = despues.get(campo)
            if isinstance(original, str) and normal is not None and original != normal:
                ajustes.append(
                    {
                        "nro_fila": nro_fila,
                        "id_cancion": _etiqueta_id(despues),
                        "campo": campo,
                        "valor_original": original,
                        "accion": f"Texto normalizado: {original!r} -> {normal!r}",
                    }
                )
    return ajustes


def resumen_general(canciones: list[Cancion]) -> dict[str, Any]:
    """Calcula las métricas globales sobre la lista de canciones válidas."""
    if not canciones:
        return {
            "total_canciones": 0,
            "total_artistas": 0,
            "total_albumes": 0,
            "conteo_tipo_album": {"album": 0, "single": 0, "compilation": 0},
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
    return ordenadas[:n]


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
    resultado: dict[str, Any] | list[Any],
    canciones: list[Cancion],
    operacion: str | None = None,
) -> None:
    """Verifica invariantes de las canciones y propiedades del resultado.

    Cada propiedad se comprueba con un cálculo distinto al que produjo el resultado,
    para que la verificación pueda fallar de verdad. `operacion` (opcional) activa la
    propiedad propia de 'top': el orden descendente por streams.
    """
    for cancion in canciones:
        if not (DURACION_MIN_PERMITIDA <= cancion.duracion_min <= DURACION_MAX_PERMITIDA):
            raise ValueError("Invariante violado: canción con duración fuera de rango.")
        if cancion.streams is not None and cancion.streams <= 0:
            raise ValueError(
                "Invariante violado: canción aceptada con streams negativos o cero sin ajustar."
            )
        if cancion.views is not None and cancion.views < 0:
            raise ValueError("Invariante violado: views negativo.")
        if cancion.likes is not None and cancion.likes < 0:
            raise ValueError("Invariante violado: likes negativo.")
        if not (ENERGY_MIN_PERMITIDA <= cancion.energy <= ENERGY_MAX_PERMITIDA):
            raise ValueError("Invariante violado: energy fuera de [0.0, 1.0].")

    total_streams_directo = sum(c.streams for c in canciones if c.streams is not None)
    streams_por_artista_album: dict[tuple[str, str], int] = {}
    for cancion in canciones:
        if cancion.streams is not None:
            clave = (cancion.artista, cancion.album)
            streams_por_artista_album[clave] = (
                streams_por_artista_album.get(clave, 0) + cancion.streams
            )

    if isinstance(resultado, dict):
        if resultado.get("total_canciones", 0) < 0 or resultado.get("streams_totales", 0) < 0:
            raise ValueError("Invariante violado: valores negativos en el resumen general.")
        if resultado.get("streams_totales", 0) != total_streams_directo:
            raise ValueError(
                "Inconsistencia en resumen: streams_totales no coincide con la suma de las canciones."
            )

    elif operacion == "top" and isinstance(resultado, list):
        for idx, cancion in enumerate(resultado):
            if cancion.streams is None or cancion.streams < 0:
                raise ValueError(
                    "Invariante violado en top: incluye una canción sin streams válidos."
                )
            if idx > 0 and cancion.streams > resultado[idx - 1].streams:
                raise ValueError(
                    "Invariante violado en top: la lista no está ordenada de forma descendente."
                )

    elif isinstance(resultado, list) and resultado:
        primero = resultado[0]
        if isinstance(primero, dict) and "album" in primero and "streams_totales" in primero:
            _verificar_albumes(resultado, streams_por_artista_album)


def _verificar_albumes(
    resultado: list[dict[str, Any]],
    streams_por_artista_album: dict[tuple[str, str], int],
) -> None:
    """Comprueba que cada fila de 'albumes' tenga la suma correcta y sea realmente el máximo."""
    for fila in resultado:
        artista = fila["artista"]
        sumas_artista = [
            total for (art, _), total in streams_por_artista_album.items() if art == artista
        ]
        if fila["streams_totales"] == "sin datos":
            if sumas_artista:
                raise ValueError(
                    f"{artista} figura 'sin datos' pero tiene canciones con streams."
                )
            continue

        total = int(fila["streams_totales"])
        if total < 0:
            raise ValueError("Invariante violado: streams_totales negativo en álbumes.")
        esperado = streams_por_artista_album.get((artista, fila["album"]), 0)
        if total != esperado:
            raise ValueError(
                f"La suma de streams del álbum '{fila['album']}' ({total}) "
                f"no coincide con el cálculo ({esperado})."
            )
        if total != max(sumas_artista):
            raise ValueError(
                f"El álbum '{fila['album']}' de {artista} no es el de mayor suma de streams "
                f"({max(sumas_artista)})."
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
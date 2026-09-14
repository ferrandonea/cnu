"""Carga y almacenamiento de tablas de mortalidad y vectores de tasas.

Las tablas y vectores incluidos en el paquete viven en ``cnu/data`` como CSV:

* ``cnu_tabmor_[tipo][agno][genero].csv`` con columnas ``edad, qx, aa``
  (tipo: ``rv`` afiliado, ``b`` beneficiario, ``mi`` invalidez; genero: ``h``/``m``).
* ``cnu_vec[agno].csv`` con columnas ``t, tasa`` (191 periodos).

Tambien se pueden leer directorios externos (``dir_tablas`` / ``dir_vectores``)
con archivos en formato CSV o en el formato binario original de Mata
(``fputmatrix``), tal como los distribuia el modulo de Stata.
"""

from __future__ import annotations

import csv
import re
import struct
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from pathlib import Path

import numpy as np

TIPOS_TABLA = ("rv", "mi", "b")
GENEROS = ("h", "m")
N_PERIODOS_VECTOR = 191

_MATA_MAGIC = b"MAT\0R"
_MATA_TRAILER = b"TAM\0JBO\0POTOM\0"


# ---------------------------------------------------------------------------
# Formato binario de Mata (fputmatrix / fgetmatrix)
# ---------------------------------------------------------------------------
def leer_matriz_mata(path: str | Path) -> np.ndarray:
    """Lee una matriz real guardada con ``fputmatrix`` de Mata."""
    datos = Path(path).read_bytes()
    i = datos.find(_MATA_MAGIC)
    if i < 0:
        raise ValueError(f"{path}: no es una matriz binaria de Mata")
    i += len(_MATA_MAGIC)
    filas, cols = struct.unpack_from("<ii", datos, i)
    i += 8
    n = filas * cols
    if len(datos) < i + 8 * n:
        raise ValueError(f"{path}: archivo truncado")
    return np.frombuffer(datos, dtype="<f8", count=n, offset=i).reshape(filas, cols).copy()


def escribir_matriz_mata(path: str | Path, matriz: np.ndarray, nombre: str = "x") -> None:
    """Escribe una matriz real en el formato binario de Mata (``fputmatrix``)."""
    m = np.ascontiguousarray(matriz, dtype="<f8")
    if m.ndim != 2:
        raise ValueError("Se requiere una matriz de dos dimensiones")
    cabecera = b"MOTOP\0\0\x02OBJ\0\0\x01" + nombre.encode() + b"\0" + b"\0" * 11 + b"\x01\0\0\0"
    cuerpo = _MATA_MAGIC + struct.pack("<ii", *m.shape) + m.tobytes()
    Path(path).write_bytes(cabecera + cuerpo + _MATA_TRAILER)


# ---------------------------------------------------------------------------
# Lectura generica (CSV o binario)
# ---------------------------------------------------------------------------
def _leer_csv(path: Path) -> np.ndarray:
    return np.loadtxt(path, delimiter=",", skiprows=1, ndmin=2)


def _buscar_archivo(nombre: str, directorio: str | Path | None) -> Path | None:
    """Busca ``nombre.csv`` o ``nombre`` (binario Mata) en ``directorio``."""
    if directorio is None:
        return None
    d = Path(directorio)
    if not d.is_dir():
        raise FileNotFoundError(f"El directorio -{d}- no fue encontrado")
    for candidato in (d / f"{nombre}.csv", d / nombre):
        if candidato.is_file():
            return candidato
    return None


def _leer_archivo(path: Path) -> np.ndarray:
    if path.suffix == ".csv":
        return _leer_csv(path)
    return leer_matriz_mata(path)


def _leer_empaquetado(nombre: str) -> np.ndarray | None:
    ref = resources.files("cnu") / "data" / f"{nombre}.csv"
    if not ref.is_file():
        return None
    with resources.as_file(ref) as p:
        return _leer_csv(p)


def _cargar(nombre: str, directorio: str | Path | None, descripcion: str) -> np.ndarray:
    ruta = _buscar_archivo(nombre, directorio)
    if ruta is not None:
        return _leer_archivo(ruta)
    if directorio is None:
        m = _leer_empaquetado(nombre)
        if m is not None:
            return m
    raise FileNotFoundError(f"{descripcion} {nombre} no existe")


# ---------------------------------------------------------------------------
# Tablas de mortalidad
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class TablaMortalidad:
    """Tabla de mortalidad con factores de mejoramiento.

    ``qx[e]`` y ``aa[e]`` estan indexados por edad ``e`` (0..edad_maxima); las
    edades que la tabla no cubre quedan en ``nan``.
    """

    tipo: str
    agno: int
    genero: str
    edades: np.ndarray
    qx: np.ndarray
    aa: np.ndarray

    @classmethod
    def desde_matriz(cls, tipo: str, agno: int, genero: str, matriz: np.ndarray) -> "TablaMortalidad":
        if matriz.ndim != 2 or matriz.shape[1] != 3:
            raise ValueError("La tabla debe tener 3 columnas ('edad', 'qx' y 'aa')")
        edades = matriz[:, 0]
        if np.any(edades < 0) or np.any(edades != np.round(edades)):
            raise ValueError("La columna de edades debe contener enteros no negativos")
        edad_max = int(edades.max())
        qx = np.full(edad_max + 1, np.nan)
        aa = np.full(edad_max + 1, np.nan)
        idx = edades.astype(int)
        qx[idx] = matriz[:, 1]
        aa[idx] = matriz[:, 2]
        return cls(tipo, int(agno), genero, idx, qx, aa)

    @property
    def nombre(self) -> str:
        return nombre_tabla(self.tipo, self.agno, self.genero)

    @property
    def edad_maxima(self) -> int:
        return len(self.qx) - 1

    def como_matriz(self) -> np.ndarray:
        return np.column_stack([self.edades, self.qx[self.edades], self.aa[self.edades]])

    def qx_mejorado(self, agno_actual: int, edad: int) -> np.ndarray:
        """Aplica el factor de mejoramiento (``cnu_mejorar_tabla`` en Mata).

        Devuelve ``qx * (1 - aa) ** (agno_actual - agno_tabla + edades - edad)``,
        indexado por edad.
        """
        dif = agno_actual - self.agno
        edades = np.arange(len(self.qx))
        return self.qx * (1.0 - self.aa) ** (dif + edades - edad)


def nombre_tabla(tipo: str, agno: int, genero: str) -> str:
    return f"cnu_tabmor_{tipo}{int(agno)}{genero}"


def parsear_nombre_tabla(nombre: str) -> tuple[str, int]:
    """``"rv2009"`` -> ``("rv", 2009)``."""
    m = re.fullmatch(r"\s*([a-zA-Z]+)(\d+)\s*", nombre)
    if not m:
        raise ValueError(f"Nombre de tabla invalido: {nombre!r} (se esperaba p.ej. 'rv2009')")
    return m.group(1).lower(), int(m.group(2))


def validar_genero(genero: str) -> str:
    if genero not in GENEROS:
        raise ValueError(f"Genero '{genero}' no permitido. Solo h o m estan permitidos")
    return genero


def genero_desde_bool(mujer: bool) -> str:
    return "m" if mujer else "h"


@lru_cache(maxsize=None)
def cargar_tabla_mortalidad(
    tipo: str, agno: int, genero: str, directorio: str | Path | None = None
) -> TablaMortalidad:
    """Carga la tabla ``cnu_tabmor_[tipo][agno][genero]``.

    Si ``directorio`` es ``None`` se usa la tabla incluida en el paquete.
    """
    validar_genero(genero)
    nombre = nombre_tabla(tipo, agno, genero)
    matriz = _cargar(nombre, directorio, "La tabla")
    return TablaMortalidad.desde_matriz(tipo, int(agno), genero, matriz)


def guardar_tabla_mortalidad(
    tabla: np.ndarray | TablaMortalidad,
    agno: int,
    genero: str,
    tipo: str,
    directorio: str | Path,
    reemplazar: bool = False,
    formato: str = "csv",
) -> Path:
    """Guarda una tabla de mortalidad (``edad, qx, aa``) en ``directorio``.

    ``formato`` puede ser ``"csv"`` o ``"mata"`` (binario original).
    """
    validar_genero(genero)
    m = tabla.como_matriz() if isinstance(tabla, TablaMortalidad) else np.asarray(tabla, dtype=float)
    if m.ndim != 2 or m.shape[1] != 3:
        raise ValueError(f"La tabla no tiene 3 columnas ('Edad', 'Qx' y 'Factor'), tiene {m.shape[-1]}")
    return _guardar(m, nombre_tabla(tipo, agno, genero), directorio, reemplazar, formato, "edad,qx,aa")


# ---------------------------------------------------------------------------
# Vectores de tasas
# ---------------------------------------------------------------------------
def nombre_vector(agno: int) -> str:
    return f"cnu_vec{int(agno)}"


@lru_cache(maxsize=None)
def cargar_vector_tasas(agno: int, directorio: str | Path | None = None) -> np.ndarray:
    """Devuelve las tasas del vector ``agno``: ``tasas[t - 1]`` es la tasa del periodo ``t``."""
    matriz = _cargar(nombre_vector(agno), directorio, "La tabla (vector de tasas)")
    if matriz.ndim != 2 or matriz.shape[1] != 2:
        raise ValueError("El vector de tasas debe tener 2 columnas ('t' y 'tasa')")
    orden = np.argsort(matriz[:, 0])
    return matriz[orden, 1].copy()


def existe_vector_tasas(agno, directorio: str | Path | None = None) -> bool:
    try:
        agno = int(agno)
    except (TypeError, ValueError):
        return False
    try:
        cargar_vector_tasas(agno, directorio)
    except (FileNotFoundError, ValueError):
        return False
    return True


def guardar_vector_tasas(
    vector: np.ndarray,
    agno: int,
    directorio: str | Path,
    reemplazar: bool = False,
    formato: str = "csv",
) -> Path:
    """Guarda un vector de tasas (``t, tasa``, 191 filas) en ``directorio``."""
    m = np.asarray(vector, dtype=float)
    if m.ndim == 1:
        m = np.column_stack([np.arange(1, len(m) + 1), m])
    if m.ndim != 2 or m.shape[1] != 2:
        raise ValueError(f"La tabla no tiene 2 columnas ('Agno' y 'Tasa'), tiene {m.shape[-1]}")
    if m.shape[0] != N_PERIODOS_VECTOR:
        raise ValueError(f"La tabla no tiene {N_PERIODOS_VECTOR} filas, tiene {m.shape[0]}")
    return _guardar(m, nombre_vector(agno), directorio, reemplazar, formato, "t,tasa")


def _guardar(m, nombre, directorio, reemplazar, formato, cabecera) -> Path:
    d = Path(directorio)
    d.mkdir(parents=True, exist_ok=True)
    if formato == "csv":
        ruta = d / f"{nombre}.csv"
    elif formato == "mata":
        ruta = d / nombre
    else:
        raise ValueError("formato debe ser 'csv' o 'mata'")
    if ruta.exists() and not reemplazar:
        raise FileExistsError(f"El archivo {ruta} ya existe, especifique reemplazar=True")
    if formato == "csv":
        with ruta.open("w", newline="") as f:
            f.write(cabecera + "\n")
            csv.writer(f).writerows(([f"{v:.17g}" for v in fila] for fila in m))
    else:
        escribir_matriz_mata(ruta, m, nombre)
    limpiar_cache()
    return ruta


def limpiar_cache() -> None:
    cargar_tabla_mortalidad.cache_clear()
    cargar_vector_tasas.cache_clear()


# ---------------------------------------------------------------------------
# Asignacion dinamica de tabla segun fecha del siniestro
# ---------------------------------------------------------------------------
def agno_tabla_por_siniestro(fsiniestro: int, tipo: str) -> int:
    """Determina el agno de tabla que corresponde a un siniestro (``cnu_which_tab_mort``).

    ``fsiniestro`` va en formato ``YYYYMMDD``.
    """
    if tipo not in TIPOS_TABLA:
        raise ValueError(f"Tipo de tabla '{tipo}' no permitido. Solo rv, mi o b estan permitidos")
    f = int(fsiniestro)
    if tipo == "rv":
        if f <= 20050131:
            return 1985
        if f <= 20100630:
            return 2004
        return 2009
    # mi y b comparten vigencias
    return 1985 if f <= 20080131 else 2006


def resolver_tabla(tabla: str, fsiniestro: int = 0) -> tuple[str, int]:
    """Devuelve ``(tipo, agno)`` para ``tabla`` (p.ej. ``"rv2009"``).

    Si ``fsiniestro`` es distinto de 0, el agno se asigna dinamicamente segun
    la normativa vigente a esa fecha.
    """
    tipo, agno = parsear_nombre_tabla(tabla)
    if fsiniestro:
        agno = agno_tabla_por_siniestro(fsiniestro, tipo)
    return tipo, agno


def tablas_disponibles() -> list[str]:
    """Nombres de las tablas de mortalidad incluidas en el paquete."""
    return sorted(
        p.name[: -len(".csv")]
        for p in (resources.files("cnu") / "data").iterdir()
        if p.name.startswith("cnu_tabmor_") and p.name.endswith(".csv")
    )


def vectores_disponibles() -> list[int]:
    """Agnos de los vectores de tasas incluidos en el paquete."""
    return sorted(
        int(p.name[len("cnu_vec") : -len(".csv")])
        for p in (resources.files("cnu") / "data").iterdir()
        if p.name.startswith("cnu_vec") and p.name.endswith(".csv")
    )

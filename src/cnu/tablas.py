"""Carga y almacenamiento de tablas de mortalidad y vectores de tasas.

Las tablas y vectores incluidos en el paquete viven en ``cnu/data`` como CSV:

* ``cnu_tabmor_[tipo][agno][genero].csv`` (tipo: ``rv`` afiliado, ``b``
  beneficiario, ``mi`` invalidez, ``cb`` combinada -solo hombres, desde 2014-;
  genero: ``h``/``m``) con dos esquemas posibles de factores de mejoramiento:

  - historico: columnas ``edad, qx, aa`` (un factor por edad);
  - bidimensional (TM2020): columnas ``edad, qx, aa2021, ..., aa2036`` (un
    factor por edad y agno calendario).

* ``cnu_vec[agno].csv`` con columnas ``t, tasa`` (191 periodos).

Tambien se pueden leer directorios externos (``dir_tablas`` / ``dir_vectores``)
con archivos en formato CSV o en el formato binario original de Mata
(``fputmatrix``), tal como los distribuia el modulo de Stata.
"""

from __future__ import annotations

import csv
import datetime
import re
import struct
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from pathlib import Path

import numpy as np

TIPOS_TABLA = ("rv", "mi", "b", "cb")
TIPOS_SOLO_HOMBRES = ("cb",)
# Nombre simbolico de tabla: se resuelve a la vigente segun rol, sexo y fecha.
TABLA_VIGENTE = "vigente"
GENEROS = ("h", "m")
CABECERA_HISTORICA = ("edad", "qx", "aa")
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
def _leer_csv(path: Path) -> tuple[np.ndarray, list[str]]:
    """Devuelve la matriz y los nombres de columna de la cabecera."""
    with open(path, newline="") as f:
        cabecera = [c.strip().lower() for c in next(csv.reader(f))]
    return np.loadtxt(path, delimiter=",", skiprows=1, ndmin=2), cabecera


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


def _leer_archivo(path: Path) -> tuple[np.ndarray, list[str] | None]:
    """Matriz y cabecera; los binarios de Mata no tienen cabecera (``None``)."""
    if path.suffix == ".csv":
        return _leer_csv(path)
    return leer_matriz_mata(path), None


def _leer_empaquetado(nombre: str) -> tuple[np.ndarray, list[str]] | None:
    ref = resources.files("cnu") / "data" / f"{nombre}.csv"
    if not ref.is_file():
        return None
    with resources.as_file(ref) as p:
        return _leer_csv(p)


def _cargar(nombre: str, directorio: str | Path | None, descripcion: str) -> tuple[np.ndarray, list[str] | None]:
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

    ``qx[e]`` esta indexado por edad ``e`` (0..edad_maxima); las edades que la
    tabla no cubre quedan en ``nan``. Los factores de mejoramiento admiten dos
    esquemas:

    * historico: ``aa[e]`` unidimensional y ``agnos_aa`` igual a ``None``;
    * bidimensional (TM2020): ``aa[e, j]`` es el factor de la edad ``e`` en el
      agno ``agnos_aa[j]`` (2021..2036).
    """

    tipo: str
    agno: int
    genero: str
    edades: np.ndarray
    qx: np.ndarray
    aa: np.ndarray
    agnos_aa: tuple[int, ...] | None = None

    @classmethod
    def desde_matriz(
        cls,
        tipo: str,
        agno: int,
        genero: str,
        matriz: np.ndarray,
        agnos_aa: tuple[int, ...] | list[int] | None = None,
    ) -> "TablaMortalidad":
        """Construye la tabla desde una matriz cruda ``edad, qx, aa...``.

        Con tres columnas la tabla es historica. Con mas de tres columnas hay
        un factor por agno y se deben entregar los ``agnos_aa`` correspondientes
        (uno por columna de factores), porque no se pueden inferir sin cabecera.
        """
        if matriz.ndim != 2 or matriz.shape[1] < 3:
            raise ValueError("La tabla debe tener al menos 3 columnas ('edad', 'qx' y 'aa')")
        n_factores = matriz.shape[1] - 2
        if n_factores == 1 and not agnos_aa:
            agnos_aa = None
        else:
            if not agnos_aa:
                raise ValueError(
                    f"La tabla tiene {n_factores} columnas de factores de mejoramiento pero no "
                    "se entregaron sus agnos (agnos_aa); use un CSV con cabecera "
                    "'edad,qx,aa2021,...' o indique agnos_aa explicitamente"
                )
            agnos_aa = tuple(int(a) for a in agnos_aa)
            if len(agnos_aa) != n_factores:
                raise ValueError(
                    f"Se entregaron {len(agnos_aa)} agnos de factores pero la tabla tiene {n_factores} columnas de factores"
                )
            if any(b <= a for a, b in zip(agnos_aa, agnos_aa[1:])):
                raise ValueError("Los agnos de los factores deben ser crecientes")
        edades = matriz[:, 0]
        if np.any(edades < 0) or np.any(edades != np.round(edades)):
            raise ValueError("La columna de edades debe contener enteros no negativos")
        edad_max = int(edades.max())
        idx = edades.astype(int)
        qx = np.full(edad_max + 1, np.nan)
        qx[idx] = matriz[:, 1]
        if agnos_aa is None:
            aa = np.full(edad_max + 1, np.nan)
            aa[idx] = matriz[:, 2]
        else:
            aa = np.full((edad_max + 1, n_factores), np.nan)
            aa[idx, :] = matriz[:, 2:]
        return cls(tipo, int(agno), genero, idx, qx, aa, agnos_aa)

    @property
    def nombre(self) -> str:
        return nombre_tabla(self.tipo, self.agno, self.genero)

    @property
    def edad_maxima(self) -> int:
        return len(self.qx) - 1

    @property
    def bidimensional(self) -> bool:
        """``True`` si los factores de mejoramiento son por edad y agno (TM2020)."""
        return self.agnos_aa is not None

    @property
    def cabecera_csv(self) -> tuple[str, ...]:
        if self.agnos_aa is None:
            return CABECERA_HISTORICA
        return ("edad", "qx", *(f"aa{a}" for a in self.agnos_aa))

    def como_matriz(self) -> np.ndarray:
        """Matriz cruda ``edad, qx, aa...`` (una columna de factores por agno si es bidimensional)."""
        return np.column_stack([self.edades, self.qx[self.edades], self.aa[self.edades]])

    def qx_mejorado(self, agno_actual: int, edad: int) -> np.ndarray:
        """Aplica el factor de mejoramiento a la tabla, indexado por edad.

        Para una persona de ``edad`` en ``agno_actual``, cada edad futura ``e``
        se evalua en su agno calendario ``a = agno_actual + e - edad``.

        * Historico (``cnu_mejorar_tabla`` en Mata):
          ``qx * (1 - aa) ** (agno_actual - agno_tabla + e - edad)``.
        * Bidimensional (TM2020, Anexo N 9 de la SP):
          ``qx(e) * prod_{t=2021..a} (1 - AA(e, min(t, 2036)))``. Si
          ``a <= 2020`` el producto es vacio y se devuelve el ``qx`` base;
          despues de 2036 se repite el factor de ese agno.
        """
        edades = np.arange(len(self.qx))
        if not self.bidimensional:
            dif = agno_actual - self.agno
            return self.qx * (1.0 - self.aa) ** (dif + edades - edad)
        return self.qx * self._factor_bidimensional(int(agno_actual) + edades - int(edad))

    def _factor_bidimensional(self, agnos: np.ndarray) -> np.ndarray:
        """``prod_{t=agnos_aa[0]..agnos[e]} (1 - AA(e, t))`` para cada edad ``e``.

        La columna de factores de un agno ``t`` es la del ultimo ``agnos_aa``
        que no lo supera (con ``agnos_aa`` consecutivos, la de ese agno); los
        agnos posteriores al ultimo repiten su factor.
        """
        agnos_aa = np.asarray(self.agnos_aa)
        primero = agnos_aa[0]
        ultimo = int(agnos.max())
        if ultimo < primero:
            return np.ones(len(self.qx))
        # Agnos calendario a cubrir y columna de factores de cada uno.
        calendario = np.arange(primero, ultimo + 1)
        columna = np.searchsorted(agnos_aa, calendario, side="right") - 1
        acumulado = np.cumprod(1.0 - self.aa[:, columna], axis=1)
        # Producto acumulado hasta el agno de cada edad (1 si es anterior al primero).
        factor = np.ones(len(self.qx))
        con_factor = agnos >= primero
        factor[con_factor] = acumulado[con_factor, agnos[con_factor] - primero]
        return factor


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


def validar_tipo(tipo: str, genero: str | None = None) -> str:
    if tipo not in TIPOS_TABLA:
        raise ValueError(f"Tipo de tabla '{tipo}' no permitido. Solo {', '.join(TIPOS_TABLA)} estan permitidos")
    if genero is not None and tipo in TIPOS_SOLO_HOMBRES and genero != "h":
        raise ValueError(f"La tabla combinada '{tipo}' solo existe para hombres (genero 'h'), no para '{genero}'")
    return tipo


def agnos_desde_cabecera(cabecera: list[str] | tuple[str, ...]) -> tuple[int, ...] | None:
    """Agnos de los factores segun la cabecera CSV.

    ``edad,qx,aa`` -> ``None`` (historica); ``edad,qx,aa2021,...`` -> ``(2021, ...)``.
    """
    cols = [c.strip().lower() for c in cabecera]
    if tuple(cols) == CABECERA_HISTORICA:
        return None
    if len(cols) < 3 or cols[:2] != ["edad", "qx"]:
        raise ValueError(f"Cabecera de tabla no reconocida: {','.join(cabecera)} (se esperaba 'edad,qx,aa' o 'edad,qx,aa2021,...')")
    agnos = []
    for c in cols[2:]:
        m = re.fullmatch(r"aa(\d{4})", c)
        if not m:
            raise ValueError(f"Columna de factores no reconocida: '{c}' (se esperaba 'aa' o 'aaYYYY')")
        agnos.append(int(m.group(1)))
    return tuple(agnos)


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
    validar_tipo(tipo, genero)
    nombre = nombre_tabla(tipo, agno, genero)
    try:
        matriz, cabecera = _cargar(nombre, directorio, "La tabla")
    except FileNotFoundError:
        if directorio is not None:
            raise
        raise FileNotFoundError(
            f"La tabla {tipo}{int(agno)}{genero} (tipo '{tipo}', agno {int(agno)}, genero '{genero}') no existe "
            "en el paquete; vea cnu.tablas_disponibles() para las combinaciones disponibles"
        ) from None
    agnos_aa = agnos_desde_cabecera(cabecera) if cabecera is not None else None
    try:
        return TablaMortalidad.desde_matriz(tipo, int(agno), genero, matriz, agnos_aa)
    except ValueError as e:
        raise ValueError(f"{nombre}: {e}") from None


def guardar_tabla_mortalidad(
    tabla: np.ndarray | TablaMortalidad,
    agno: int,
    genero: str,
    tipo: str,
    directorio: str | Path,
    reemplazar: bool = False,
    formato: str = "csv",
    agnos_aa: tuple[int, ...] | list[int] | None = None,
) -> Path:
    """Guarda una tabla de mortalidad en ``directorio``.

    ``tabla`` puede ser una :class:`TablaMortalidad` o una matriz cruda
    ``edad, qx, aa...``; con mas de tres columnas hay que entregar ``agnos_aa``
    (un agno por columna de factores). ``formato`` puede ser ``"csv"`` o
    ``"mata"`` (binario original). El binario no guarda la cabecera, asi que
    una tabla bidimensional en ese formato solo se puede recuperar con
    :meth:`TablaMortalidad.desde_matriz` indicando ``agnos_aa``.
    """
    validar_genero(genero)
    validar_tipo(tipo, genero)
    if isinstance(tabla, TablaMortalidad):
        m = tabla.como_matriz()
        cabecera = tabla.cabecera_csv
    else:
        m = np.asarray(tabla, dtype=float)
        if m.ndim != 2 or m.shape[1] < 3:
            raise ValueError(f"La tabla no tiene al menos 3 columnas ('Edad', 'Qx' y 'Factor'), tiene {m.shape[-1]}")
        # desde_matriz valida agnos_aa y el numero de columnas
        cabecera = TablaMortalidad.desde_matriz(tipo, agno, genero, m, agnos_aa).cabecera_csv
    return _guardar(m, nombre_tabla(tipo, agno, genero), directorio, reemplazar, formato, ",".join(cabecera))


# ---------------------------------------------------------------------------
# Vectores de tasas
# ---------------------------------------------------------------------------
def nombre_vector(agno: int) -> str:
    return f"cnu_vec{int(agno)}"


@lru_cache(maxsize=None)
def cargar_vector_tasas(agno: int, directorio: str | Path | None = None) -> np.ndarray:
    """Devuelve las tasas del vector ``agno``: ``tasas[t - 1]`` es la tasa del periodo ``t``."""
    matriz, _ = _cargar(nombre_vector(agno), directorio, "La tabla (vector de tasas)")
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
ROLES = ("rv", "b", "mi")

# Vigencias oficiales: (primera fecha de vigencia YYYYMMDD, agno de las
# tablas, hombres usan la tabla combinada ``cb`` en vez de ``rv``/``b``).
# Cada tramo rige desde su fecha hasta el dia anterior al tramo siguiente.
_VIGENCIAS_AFILIADO = ((0, 1985, False), (20050201, 2004, False), (20100701, 2009, False),
                       (20160701, 2014, True), (20230701, 2020, True))
_VIGENCIAS_BENEFICIARIO = ((0, 1985, False), (20080201, 2006, False),
                           (20160701, 2014, True), (20230701, 2020, True))
_VIGENCIAS_INVALIDO = ((0, 1985, False), (20080201, 2006, False),
                       (20160701, 2014, False), (20230701, 2020, False))
_VIGENCIAS = {"rv": _VIGENCIAS_AFILIADO, "b": _VIGENCIAS_BENEFICIARIO, "mi": _VIGENCIAS_INVALIDO}


def validar_rol(rol: str) -> str:
    if rol not in ROLES:
        raise ValueError(f"Rol '{rol}' no permitido. Solo {', '.join(ROLES)} estan permitidos")
    return rol


def tabla_por_fecha(fecha: int, rol: str, genero: str) -> tuple[str, int]:
    """Tipo y agno de la tabla vigente a la ``fecha`` (``YYYYMMDD``) del siniestro.

    ``rol`` es ``rv`` (afiliado), ``b`` (beneficiario) o ``mi`` (invalido) y
    ``genero`` es ``h`` o ``m``. Desde el 1 de julio de 2016 los hombres no
    invalidos usan la tabla combinada ``cb`` (afiliados y beneficiarios):

    ======================  ========  ========  ========  ========  ========
    Fecha                   Afil. H   Afil. M   Benef. H  Benef. M  Invalido
    ======================  ========  ========  ========  ========  ========
    hasta 31-01-2005        rv1985    rv1985    b1985     b1985     mi1985
    01-02-2005 a 31-01-2008 rv2004    rv2004    b1985     b1985     mi1985
    01-02-2008 a 30-06-2010 rv2004    rv2004    b2006     b2006     mi2006
    01-07-2010 a 30-06-2016 rv2009    rv2009    b2006     b2006     mi2006
    01-07-2016 a 30-06-2023 cb2014    rv2014    cb2014    b2014     mi2014
    desde 01-07-2023        cb2020    rv2020    cb2020    b2020     mi2020
    ======================  ========  ========  ========  ========  ========
    """
    validar_rol(rol)
    validar_genero(genero)
    f = int(fecha)
    agno, combinada = None, False
    for desde, agno_tramo, combinada_tramo in _VIGENCIAS[rol]:
        if f < desde:
            break
        agno, combinada = agno_tramo, combinada_tramo
    tipo = "cb" if combinada and genero == "h" else rol
    return tipo, agno


def agno_tabla_por_siniestro(fsiniestro: int, tipo: str) -> int:
    """Agno de la tabla vigente a la fecha del siniestro (``cnu_which_tab_mort``).

    ``fsiniestro`` va en formato ``YYYYMMDD`` y ``tipo`` es el rol (``rv``,
    ``b`` o ``mi``). El agno no depende del sexo; vease
    :func:`tabla_por_fecha` para obtener tambien el tipo (``cb`` para hombres
    desde 2016).
    """
    if tipo not in ROLES:
        raise ValueError(f"Tipo de tabla '{tipo}' no permitido. Solo rv, mi o b estan permitidos")
    return tabla_por_fecha(fsiniestro, tipo, "h")[1]


def es_tabla_vigente(tabla: str) -> bool:
    """``True`` si ``tabla`` es el nombre simbolico :data:`TABLA_VIGENTE`."""
    return isinstance(tabla, str) and tabla.strip().lower() == TABLA_VIGENTE


def fecha_fin_de_agno(agno: int) -> int:
    """31 de diciembre de ``agno`` en formato ``YYYYMMDD`` (convencion de fin de agno)."""
    return int(agno) * 10000 + 1231


def resolver_tabla(
    tabla: str,
    fsiniestro: int = 0,
    rol: str | None = None,
    genero: str | None = None,
    agno_actual: int | None = None,
) -> tuple[str, int]:
    """Devuelve ``(tipo, agno)`` para ``tabla`` (p.ej. ``"rv2009"`` o ``"vigente"``).

    * Nombre explicito (``"rv2009"``, ``"cb2020"``, ...): se respeta tal cual.
      Si ``fsiniestro`` es distinto de 0 la tabla se asigna dinamicamente
      segun la normativa vigente a esa fecha con :func:`tabla_por_fecha`,
      usando el ``rol`` (por defecto, el tipo del nombre) y el ``genero`` de
      la persona. Sin ``genero`` solo se reasigna el agno y se conserva el
      tipo del nombre (comportamiento del modulo de Stata).
    * :data:`TABLA_VIGENTE` (``"vigente"``): requiere ``rol`` y ``genero``.
      Con ``fsiniestro`` se usa la fecha del siniestro; sin ``fsiniestro`` se
      aplica la convencion de fin de agno, el 31 de diciembre de
      ``agno_actual`` (por defecto, el agno en curso). Asi 2016 y 2023
      resuelven a la vigencia nueva (TM2014 y TM2020, respectivamente).
    """
    if es_tabla_vigente(tabla):
        if rol is None or genero is None:
            raise ValueError("La tabla 'vigente' requiere el rol (rv, b o mi) y el genero (h o m) de la persona")
        if not fsiniestro:
            if agno_actual is None:
                agno_actual = datetime.date.today().year
            fsiniestro = fecha_fin_de_agno(agno_actual)
        return tabla_por_fecha(fsiniestro, rol, genero)
    tipo, agno = parsear_nombre_tabla(tabla)
    if fsiniestro:
        rol = rol or tipo
        if genero is None:
            agno = agno_tabla_por_siniestro(fsiniestro, rol)
        else:
            tipo, agno = tabla_por_fecha(fsiniestro, rol, genero)
    return tipo, agno


def tablas_disponibles() -> list[str]:
    """Nombres de las tablas de mortalidad incluidas en el paquete."""
    return sorted(
        p.name[: -len(".csv")]
        for p in (resources.files("cnu") / "data").iterdir()
        if p.name.startswith("cnu_tabmor_") and p.name.endswith(".csv")
    )


def describir_tabla(nombre: str) -> str:
    """Descripcion corta de una tabla incluida: edades y esquema de factores."""
    m = re.fullmatch(r"cnu_tabmor_([a-z]+)(\d+)([hm])", nombre)
    if not m:
        raise ValueError(f"Nombre de tabla no reconocido: {nombre}")
    t = cargar_tabla_mortalidad(m.group(1), int(m.group(2)), m.group(3))
    edades = f"edades {int(t.edades.min())}-{int(t.edades.max())}"
    if t.bidimensional:
        return f"{edades}, factores bidimensionales {t.agnos_aa[0]}-{t.agnos_aa[-1]}"
    return f"{edades}, factor historico"


def vectores_disponibles() -> list[int]:
    """Agnos de los vectores de tasas incluidos en el paquete."""
    return sorted(
        int(p.name[len("cnu_vec") : -len(".csv")])
        for p in (resources.files("cnu") / "data").iterdir()
        if p.name.startswith("cnu_vec") and p.name.endswith(".csv")
    )

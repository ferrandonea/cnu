"""Formulas escalares del Capital Necesario Unitario (CNU).

Equivalentes a las rutinas Mata ``cnu_2_1`` (afiliado), ``cnu_2_2`` (conyuge
sin hijos) y ``cnu_1_1`` (sobrevivencia para conyuge sin hijos), segun el
Anexo N 7 del Compendio de Normas de la Superintendencia de Pensiones.

Seleccion de la tasa de descuento (misma regla que el modulo de Stata):

* ``rv`` dado  -> Renta Vitalicia con tasa constante ``rv``.
* ``rp`` dado  -> Retiro Programado con tasa constante ``rp``.
* ninguno      -> Retiro Programado con el vector de tasas ``agno_vector``.
"""

from __future__ import annotations

import datetime as _dt
import math

import numpy as np

from .tablas import (
    N_PERIODOS_VECTOR,
    TABLA_VIGENTE,
    TablaMortalidad,
    cargar_tabla_mortalidad,
    cargar_vector_tasas,
    genero_desde_bool,
    resolver_tabla,
)

EDAD_MINIMA = 20
EDAD_MAXIMA = 110
AJUSTE_MENSUAL = 11 / 24  # descuento por pago mensual (11/24 de una anualidad)
FRACCION_CONYUGE = 0.6

# Por defecto se usa la tabla vigente para el rol, sexo y fecha de calculo
# (fecha del siniestro o, en su defecto, el 31 de diciembre de ``agno_actual``).
TABLA_AFILIADO = TABLA_VIGENTE
TABLA_BENEFICIARIO = TABLA_VIGENTE
AGNO_VECTOR = 2013

# Roles de la persona cuya mortalidad se modela; coinciden con el tipo de
# tabla historico (rv afiliado, b beneficiario, mi invalido).
ROL_AFILIADO = "rv"
ROL_BENEFICIARIO = "b"
ROL_INVALIDO = "mi"


def agno_actual_por_defecto() -> int:
    return _dt.date.today().year


def _agno(agno_actual: int | None) -> int:
    return agno_actual_por_defecto() if agno_actual is None else int(agno_actual)


def tasas_por_periodo(
    agno_vector: int = AGNO_VECTOR,
    rv: float | None = None,
    rp: float | None = None,
    dir_vectores=None,
) -> np.ndarray:
    """Vector de tasas por periodo (``tasas[t-1]`` para el periodo ``t``)."""
    if rv is not None and not _es_missing(rv):
        return np.full(N_PERIODOS_VECTOR, float(rv))
    if rp is not None and not _es_missing(rp):
        return np.full(N_PERIODOS_VECTOR, float(rp))
    return cargar_vector_tasas(int(agno_vector), dir_vectores)


def _es_missing(v) -> bool:
    try:
        return math.isnan(v)
    except TypeError:
        return False


def _redondear(v: float) -> float:
    return round(float(v), 6)


def _qx_hasta(qx: np.ndarray, edad_maxima: int) -> np.ndarray:
    """Extiende ``qx`` con 1.0 hasta ``edad_maxima`` (nadie sobrevive mas alla de la tabla).

    Las tablas historicas llegan a 210 agnos, pero las TM2014/TM2020 terminan
    en 110 con ``qx = 1``; el CNU de conyuge recorre edades del afiliado
    mayores que 110 cuando el conyuge es menor, y su ``lx`` ya es 0.
    """
    if len(qx) > edad_maxima:
        return qx
    return np.concatenate([qx, np.ones(edad_maxima + 1 - len(qx))])


def tabla_mortalidad(
    tabla: str,
    rol: str,
    mujer: bool,
    fsiniestro: int = 0,
    agno_actual: int | None = None,
    dir_tablas=None,
) -> TablaMortalidad:
    """Punto unico de resolucion de tablas de mortalidad.

    Traduce el nombre ``tabla`` (p.ej. ``"rv2009"`` o ``"vigente"``) a la
    tabla cargada que corresponde a una persona con el ``rol`` dado
    (:data:`ROL_AFILIADO`, :data:`ROL_BENEFICIARIO` o :data:`ROL_INVALIDO`) y
    sexo ``mujer``:

    * nombre explicito: se respeta tal cual; con ``fsiniestro`` la tabla
      (tipo y agno) se asigna segun la vigencia a esa fecha;
    * ``"vigente"``: la tabla vigente a ``fsiniestro`` o, si no se entrega,
      al 31 de diciembre de ``agno_actual`` (convencion de fin de agno).

    :param fsiniestro: fecha del siniestro ``YYYYMMDD`` (0 si no se conoce).
    :param agno_actual: agno de calculo (por defecto, el del sistema); solo
        interviene al resolver ``"vigente"`` sin ``fsiniestro``.
    """
    genero = genero_desde_bool(mujer)
    tipo, agno_tabla = resolver_tabla(tabla, fsiniestro, rol, genero, _agno(agno_actual))
    return cargar_tabla_mortalidad(tipo, agno_tabla, genero, dir_tablas)


def nombre_tabla_resuelta(
    tabla: str,
    rol: str,
    mujer: bool,
    fsiniestro: int = 0,
    agno_actual: int | None = None,
    dir_tablas=None,
) -> str:
    """Nombre explicito (tipo y agno, p.ej. ``"cb2020"``) de la tabla resuelta.

    Fija el resultado de :func:`tabla_mortalidad` para reutilizarlo en varios
    calculos (p.ej. una proyeccion) sin volver a resolver ``"vigente"``.
    """
    tm = tabla_mortalidad(tabla, rol, mujer, fsiniestro, agno_actual, dir_tablas)
    return f"{tm.tipo}{tm.agno}"


def _etiqueta_tabla(tm: TablaMortalidad) -> str:
    """Tabla efectivamente resuelta: tipo, agno y sexo (p.ej. ``cb2020h``)."""
    return f"{tm.tipo}{tm.agno}{tm.genero}"


def cnu_afiliado(
    x: int,
    mujer: bool = False,
    tabla: str = TABLA_AFILIADO,
    agno_vector: int = AGNO_VECTOR,
    agno_actual: int | None = None,
    rv: float | None = None,
    rp: float | None = None,
    fsiniestro: int = 0,
    pasos: bool = False,
    dir_tablas=None,
    dir_vectores=None,
) -> float:
    """CNU para afiliado (punto 2.1 del anexo). Equivale a ``cnu_afili`` / ``cnu_2_1``.

    :param x: edad del afiliado.
    :param mujer: ``True`` si el afiliado es mujer.
    :param tabla: tabla de mortalidad del afiliado, p.ej. ``"rv2009"``; por
        defecto ``"vigente"`` (ver :func:`tabla_mortalidad`).
    :param agno_vector: agno del vector de tasas (retiro programado).
    :param agno_actual: agno de calculo (por defecto, el del sistema); con
        ``"vigente"`` y sin ``fsiniestro`` la tabla es la vigente al 31 de
        diciembre de este agno.
    :param rv: tasa de renta vitalicia; si se entrega, el CNU es de RV.
    :param rp: tasa unica de retiro programado (reemplaza al vector).
    :param fsiniestro: fecha del siniestro ``YYYYMMDD``; si es distinta de 0,
        el agno de la tabla se asigna dinamicamente.
    :param pasos: imprime el calculo periodo a periodo.
    """
    x = int(x)
    agno_actual = _agno(agno_actual)
    tm = tabla_mortalidad(tabla, ROL_AFILIADO, mujer, fsiniestro, agno_actual, dir_tablas)
    qx = tm.qx_mejorado(agno_actual, x)
    tasas = tasas_por_periodo(agno_vector, rv, rp, dir_vectores)

    tmax = EDAD_MAXIMA - x + 1
    cnu = 1.0
    lxt = 1.0
    if pasos:
        print(f"tabla {_etiqueta_tabla(tm)}")
        print("t =   0: CNU = 1")
    for t in range(1, tmax + 1):
        lxt *= 1.0 - qx[x + t - 1]
        i = tasas[t - 1]
        if pasos:
            print(f"t = {t:3d}: cnu = {cnu:9.6f} + {lxt:g}/((1 + {i:g})^{t})")
        cnu += lxt / (1.0 + i) ** t
    return _redondear(cnu - AJUSTE_MENSUAL)


def cnu_conyuge(
    x: int,
    y: int,
    cot_mujer: bool = False,
    cony_mujer: bool = True,
    tabla: str = TABLA_AFILIADO,
    tabla_benef: str = TABLA_BENEFICIARIO,
    agno_vector: int = AGNO_VECTOR,
    agno_actual: int | None = None,
    rv: float | None = None,
    rp: float | None = None,
    fsiniestro: int = 0,
    pasos: bool = False,
    dir_tablas=None,
    dir_vectores=None,
) -> float:
    """CNU para conyuge sin hijos de un afiliado (pension de vejez).

    Equivale a ``cnu_cnyg_s_hi`` / ``cnu_2_2``. El resultado se suma al de
    :func:`cnu_afiliado` para obtener el CNU total.

    :param x: edad del afiliado.
    :param y: edad del conyuge.
    :param cot_mujer: ``True`` si el afiliado es mujer.
    :param cony_mujer: ``True`` si el conyuge es mujer.
    :param tabla: tabla del afiliado (p.ej. ``"rv2009"``; por defecto ``"vigente"``).
    :param tabla_benef: tabla del beneficiario (p.ej. ``"b2006"``; por defecto ``"vigente"``).
    """
    x, y = int(x), int(y)
    agno_actual = _agno(agno_actual)
    tm_cot = tabla_mortalidad(tabla, ROL_AFILIADO, cot_mujer, fsiniestro, agno_actual, dir_tablas)
    tm_cony = tabla_mortalidad(tabla_benef, ROL_BENEFICIARIO, cony_mujer, fsiniestro, agno_actual, dir_tablas)
    tmax = EDAD_MAXIMA - y + 1
    qx_cot = _qx_hasta(tm_cot.qx_mejorado(agno_actual, x), x + tmax - 1)
    qx_cony = tm_cony.qx_mejorado(agno_actual, y)
    tasas = tasas_por_periodo(agno_vector, rv, rp, dir_vectores)

    cnu = 0.0
    lxt = 1.0
    lyt = 1.0
    if pasos:
        print(f"tablas {_etiqueta_tabla(tm_cot)} {_etiqueta_tabla(tm_cony)}")
        print("t =   0: CNU = 1")
    for t in range(1, tmax + 1):
        i = tasas[t - 1]
        lxt *= 1.0 - qx_cot[x + t - 1]
        lyt *= 1.0 - qx_cony[y + t - 1]
        if pasos:
            print(f"t = {t:3d}: cnu = {cnu:9.6f} + ({lyt:g}/(1 + {i:g})^{t})*(1 - {lxt:g})")
        cnu += lyt / (1.0 + i) ** t * (1.0 - lxt)
    return _redondear(FRACCION_CONYUGE * cnu)


def cnu_sobrevivencia_conyuge(
    y: int,
    mujer: bool = False,
    tabla_benef: str = TABLA_BENEFICIARIO,
    agno_vector: int = AGNO_VECTOR,
    agno_actual: int | None = None,
    rv: float | None = None,
    rp: float | None = None,
    fsiniestro: int = 0,
    pasos: bool = False,
    dir_tablas=None,
    dir_vectores=None,
) -> float:
    """CNU de pension de sobrevivencia para conyuge sin hijos.

    Equivale a ``cnu_sobr_cnyg_s_hi`` / ``cnu_1_1``.

    :param y: edad del conyuge.
    :param mujer: ``True`` si el conyuge es mujer.
    :param tabla_benef: tabla de mortalidad del beneficiario (p.ej. ``"b2006"``;
        por defecto ``"vigente"``).
    """
    y = int(y)
    agno_actual = _agno(agno_actual)
    tm = tabla_mortalidad(tabla_benef, ROL_BENEFICIARIO, mujer, fsiniestro, agno_actual, dir_tablas)
    qx = tm.qx_mejorado(agno_actual, y)
    tasas = tasas_por_periodo(agno_vector, rv, rp, dir_vectores)

    tmax = EDAD_MAXIMA - y
    cnu = 1.0
    lyt = 1.0
    if pasos:
        print(f"tabla {_etiqueta_tabla(tm)}")
        print("t =   0: CNU = 1")
    for t in range(1, tmax + 1):
        lyt *= 1.0 - qx[y + t - 1]
        i = tasas[t - 1]
        if pasos:
            print(f"t = {t:3d}: cnu = {cnu:9.6f} + {lyt:g}/((1 + {i:g})^{t})")
        cnu += lyt / (1.0 + i) ** t
    return _redondear(FRACCION_CONYUGE * (cnu - AJUSTE_MENSUAL))


def describir(
    tipo_cnu: str,
    tabla: str | None = None,
    tabla_benef: str | None = None,
    agno_vector: int = AGNO_VECTOR,
    agno_actual: int | None = None,
    rv: float | None = None,
    rp: float | None = None,
    fsiniestro: int = 0,
    mujer: bool = False,
    benef_mujer: bool = True,
    dir_tablas=None,
) -> str:
    """Etiqueta descriptiva del calculo, al estilo de los comandos de Stata.

    ``tabla`` es la del afiliado (sexo ``mujer``) y ``tabla_benef`` la del
    beneficiario (sexo ``benef_mujer``). Se muestran las tablas efectivamente
    resueltas (tipo, agno y sexo), p.ej. ``cb2020h`` con ``fsiniestro`` de 2024.
    """
    agno_actual = _agno(agno_actual)
    tablas = []
    for t, rol, es_mujer in ((tabla, ROL_AFILIADO, mujer), (tabla_benef, ROL_BENEFICIARIO, benef_mujer)):
        if t:
            tm = tabla_mortalidad(t, rol, es_mujer, fsiniestro, agno_actual, dir_tablas)
            tablas.append(_etiqueta_tabla(tm))
    etiqueta_tablas = ("tablas " if len(tablas) > 1 else "tabla ") + " ".join(tablas)
    if rv is not None:
        return f"CNU RV para {tipo_cnu} ({etiqueta_tablas}), tasa {rv * 100:g}% en el año {agno_actual}"
    if rp is not None:
        return f"CNU RP para {tipo_cnu} ({etiqueta_tablas}), tasa {rp * 100:g}% en el año {agno_actual}"
    return f"CNU RP para {tipo_cnu} ({etiqueta_tablas}), vector {agno_vector} en el año {agno_actual}"

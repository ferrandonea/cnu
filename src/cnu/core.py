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
    cargar_tabla_mortalidad,
    cargar_vector_tasas,
    genero_desde_bool,
    resolver_tabla,
)

EDAD_MINIMA = 20
EDAD_MAXIMA = 110
AJUSTE_MENSUAL = 11 / 24  # descuento por pago mensual (11/24 de una anualidad)
FRACCION_CONYUGE = 0.6

TABLA_AFILIADO = "rv2009"
TABLA_BENEFICIARIO = "b2006"
AGNO_VECTOR = 2013


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
    :param tabla: tabla de mortalidad del afiliado, p.ej. ``"rv2009"``.
    :param agno_vector: agno del vector de tasas (retiro programado).
    :param agno_actual: agno de calculo (por defecto, el del sistema).
    :param rv: tasa de renta vitalicia; si se entrega, el CNU es de RV.
    :param rp: tasa unica de retiro programado (reemplaza al vector).
    :param fsiniestro: fecha del siniestro ``YYYYMMDD``; si es distinta de 0,
        el agno de la tabla se asigna dinamicamente.
    :param pasos: imprime el calculo periodo a periodo.
    """
    x = int(x)
    agno_actual = _agno(agno_actual)
    tipo, agno_tabla = resolver_tabla(tabla, fsiniestro)
    tm = cargar_tabla_mortalidad(tipo, agno_tabla, genero_desde_bool(mujer), dir_tablas)
    qx = tm.qx_mejorado(agno_actual, x)
    tasas = tasas_por_periodo(agno_vector, rv, rp, dir_vectores)

    tmax = EDAD_MAXIMA - x + 1
    cnu = 1.0
    lxt = 1.0
    if pasos:
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
    :param tabla: tabla del afiliado (p.ej. ``"rv2009"``).
    :param tabla_benef: tabla del beneficiario (p.ej. ``"b2006"``).
    """
    x, y = int(x), int(y)
    agno_actual = _agno(agno_actual)
    tipo_cot, agno_cot = resolver_tabla(tabla, fsiniestro)
    tipo_cony, agno_cony = resolver_tabla(tabla_benef, fsiniestro)
    tm_cot = cargar_tabla_mortalidad(tipo_cot, agno_cot, genero_desde_bool(cot_mujer), dir_tablas)
    tm_cony = cargar_tabla_mortalidad(tipo_cony, agno_cony, genero_desde_bool(cony_mujer), dir_tablas)
    qx_cot = tm_cot.qx_mejorado(agno_actual, x)
    qx_cony = tm_cony.qx_mejorado(agno_actual, y)
    tasas = tasas_por_periodo(agno_vector, rv, rp, dir_vectores)

    tmax = EDAD_MAXIMA - y + 1
    cnu = 0.0
    lxt = 1.0
    lyt = 1.0
    if pasos:
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
    :param tabla_benef: tabla de mortalidad del beneficiario (p.ej. ``"b2006"``).
    """
    y = int(y)
    agno_actual = _agno(agno_actual)
    tipo, agno_tabla = resolver_tabla(tabla_benef, fsiniestro)
    tm = cargar_tabla_mortalidad(tipo, agno_tabla, genero_desde_bool(mujer), dir_tablas)
    qx = tm.qx_mejorado(agno_actual, y)
    tasas = tasas_por_periodo(agno_vector, rv, rp, dir_vectores)

    tmax = EDAD_MAXIMA - y
    cnu = 1.0
    lyt = 1.0
    if pasos:
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
) -> str:
    """Etiqueta descriptiva del calculo, al estilo de los comandos de Stata."""
    agno_actual = _agno(agno_actual)
    tablas = []
    for t in (tabla, tabla_benef):
        if t:
            tipo, agno = resolver_tabla(t, fsiniestro)
            tablas.append(f"{tipo}{agno}")
    etiqueta_tablas = ("tablas " if len(tablas) > 1 else "tabla ") + " ".join(tablas)
    if rv is not None:
        return f"CNU RV para {tipo_cnu} ({etiqueta_tablas}), tasa {rv * 100:g}% en el año {agno_actual}"
    if rp is not None:
        return f"CNU RP para {tipo_cnu} ({etiqueta_tablas}), tasa {rp * 100:g}% en el año {agno_actual}"
    return f"CNU RP para {tipo_cnu} ({etiqueta_tablas}), vector {agno_vector} en el año {agno_actual}"

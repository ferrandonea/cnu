"""Factor de Ajuste (FAJ) para Retiros Programados.

Equivale a ``cnu_faj.mata`` (``cnu_faj_fun_obj``, ``cnu_faj`` y ``cnu_faj_vec``)
y a los comandos ``cnu_faji`` (escalar) y ``cnu_faj`` (vectorial) de Stata.
"""

from __future__ import annotations

import math
import warnings

import numpy as np

from . import core
from .core import AGNO_VECTOR, EDAD_MAXIMA, EDAD_MINIMA, TABLA_AFILIADO, TABLA_BENEFICIARIO

EDAD_MAXIMA_FAJ = 98
PCENT = 0.3
CRITERIO = 1e-6
MAXITER = 100


def faj_funcion_objetivo(
    faj: float,
    x: int,
    cnu,
    rp_a,
    edad_maxima: int = EDAD_MAXIMA_FAJ,
    saldo: float = 1.0,
    pcent: float = PCENT,
    rp0: float | None = None,
) -> float:
    """Funcion objetivo que se minimiza para encontrar el FAJ (``cnu_faj_fun_obj``).

    :param cnu: trayectoria del CNU desde la edad ``x`` (ver :func:`cnu.proyectar_cnu`).
    :param rp_a: tasa anual de RP por periodo (arreglo).
    :param rp0: pension de referencia; por defecto ``saldo / cnu[0]``.
    """
    cnu = np.asarray(cnu, dtype=float)
    rp_a = np.asarray(rp_a, dtype=float)
    if rp0 is None or core._es_missing(rp0):
        rp0 = saldo / cnu[0]
    suma = 0.0
    saldo_t = saldo
    for t in range(0, int(edad_maxima) - core.edad_entera(x) + 1):
        pens_t = saldo_t / cnu[t]
        saldo_t = (saldo_t - pens_t) * (1 + rp_a[t])
        suma += (pens_t - max((1 - faj) * pens_t, pcent * rp0)) / (1 + rp_a[t]) ** (t + 1)
    return suma


def calcular_faj(
    x: int,
    cnu,
    rp_a,
    edad_maxima: int = EDAD_MAXIMA_FAJ,
    saldo: float = 1.0,
    pcent: float = PCENT,
    rp0: float | None = None,
    criter: float = 1e-7,
    maxiter: int = MAXITER,
) -> float:
    """Busca el FAJ optimo por busqueda ternaria en [0, 1] (``cnu_faj`` en Mata)."""
    if edad_maxima is None or core._es_missing(edad_maxima):
        edad_maxima = EDAD_MAXIMA_FAJ
    minr, maxr = 0.0, 1.0
    rango = maxr - minr
    faj1 = faj2 = val1 = val2 = None
    niter = 0
    while rango > criter:
        niter += 1
        if niter >= maxiter:
            break
        faj1 = minr + rango / 3
        faj2 = minr + rango / 3 * 2
        val1 = faj_funcion_objetivo(faj1, x, cnu, rp_a, edad_maxima, saldo, pcent, rp0)
        val2 = faj_funcion_objetivo(faj2, x, cnu, rp_a, edad_maxima, saldo, pcent, rp0)
        if val1 < val2 and val1 > 0:
            maxr = faj2
        else:
            minr = faj1
        rango = maxr - minr
    if faj1 is None:
        raise ValueError("criter debe ser menor que 1 para que la busqueda itere")
    return faj1 if val1 < val2 else faj2


def faj_afiliado(
    x: int,
    y: int | None = None,
    cot_mujer: bool = False,
    cony_mujer: bool = True,
    tabla: str = TABLA_AFILIADO,
    tabla_benef: str = TABLA_BENEFICIARIO,
    agno_vector: int = AGNO_VECTOR,
    agno_actual: int | None = None,
    rp: float | None = 0.03,
    fsiniestro: int = 0,
    edad_maxima: int = EDAD_MAXIMA_FAJ,
    saldo: float = 1.0,
    pcent: float = PCENT,
    rp0: float | None = None,
    criter: float = CRITERIO,
    maxiter: int = MAXITER,
    dir_tablas=None,
    dir_vectores=None,
) -> float:
    """FAJ para un afiliado, con o sin conyuge (equivale a ``cnu_faji``).

    Igual que el comando de Stata, la trayectoria del CNU se calcula siempre
    con el vector de tasas ``agno_vector``; ``rp`` (tasa unica, o ``None`` para
    usar el vector) solo interviene en la capitalizacion del saldo.

    Las tablas ``tabla`` (afiliado, sexo ``cot_mujer``) y ``tabla_benef``
    (beneficiario, sexo ``cony_mujer``), por defecto ``"vigente"``, se
    resuelven una sola vez al inicio (``fsiniestro`` o el 31 de diciembre de
    ``agno_actual``) y se usan en toda la trayectoria del CNU
    (:func:`cnu.proyectar_cnu`).
    """
    from .proyeccion import proyectar_cnu  # importacion diferida (ciclo)

    x = core.edad_entera(x)
    cnu = proyectar_cnu(
        x, y, cot_mujer, cony_mujer, tabla, tabla_benef, agno_vector, agno_actual,
        None, None, fsiniestro, dir_tablas, dir_vectores,
    )
    rp_a = core.tasas_por_periodo(agno_vector, None, rp, dir_vectores, fsiniestro)
    return calcular_faj(x, cnu, rp_a, edad_maxima, saldo, pcent, rp0, criter, maxiter)


def faj_afiliado_vec(
    x,
    y=None,
    cot_mujer=False,
    cony_mujer=False,
    tabla=TABLA_AFILIADO,
    tabla_benef=TABLA_BENEFICIARIO,
    agno_vector=AGNO_VECTOR,
    agno_actual=None,
    rp=None,
    fsiniestro=0,
    edad_maxima=EDAD_MAXIMA_FAJ,
    saldo=1.0,
    pcent=PCENT,
    rp0=None,
    criter: float = CRITERIO,
    maxiter: int = MAXITER,
    incluir=None,
    dir_tablas=None,
    dir_vectores=None,
) -> np.ndarray:
    """FAJ para varias observaciones (equivale a ``cnu_faj`` vectorial).

    A diferencia de :func:`faj_afiliado`, aqui ``rp`` (si se entrega) se usa
    tambien como tasa constante para la trayectoria del CNU; si es ``None``
    (o ``nan`` en la fila) se usa el vector ``agno_vector``: la tasa del
    periodo ``j`` del vector se aplica como tasa constante al CNU del periodo
    ``j`` (comportamiento heredado de ``cnu_faj_vec``).

    Las tablas (por defecto ``"vigente"``) se resuelven por fila, con el rol,
    el sexo y la fecha de cada observacion, al inicio de su trayectoria.
    """
    from .proyeccion import proyectar_cnu  # importacion diferida (ciclo)
    from .vectorial import AdvertenciaCNU, _preparar

    x = np.atleast_1d(np.asarray(x, dtype=float))
    n = len(x)
    a = _preparar(n, y=y, cot_mujer=cot_mujer, cony_mujer=cony_mujer, tabla=tabla, tabla_benef=tabla_benef,
                  agno_vector=agno_vector, agno_actual=agno_actual, rp=rp, fsiniestro=fsiniestro,
                  edad_maxima=edad_maxima, saldo=saldo, pcent=pcent, rp0=rp0, incluir=incluir)
    faj = np.full(n, np.nan)
    sin_vector = []
    for i in range(n):
        if not a["incluir"][i] or math.isnan(x[i]):
            continue
        xi = core.edad_entera(x[i])
        if xi < EDAD_MINIMA or xi > EDAD_MAXIMA:
            continue
        agno_vec = int(a["agno_vector"][i])
        rp_a = core.tasas_por_periodo(
            agno_vec, None, a["rp"][i], dir_vectores, int(a["fsiniestro"][i]), estricto=False
        )
        if rp_a is None:
            sin_vector.append(i)
            continue
        yi = None if math.isnan(a["y"][i]) else core.edad_entera(a["y"][i])
        agno_act = None if math.isnan(a["agno_actual"][i]) else int(a["agno_actual"][i])
        cnu = proyectar_cnu(
            xi, yi, bool(a["cot_mujer"][i]), bool(a["cony_mujer"][i]), a["tabla"][i], a["tabla_benef"][i],
            agno_vec, agno_act, None, rp_a, int(a["fsiniestro"][i]), dir_tablas, dir_vectores,
        )
        rp0_i = None if math.isnan(a["rp0"][i]) else float(a["rp0"][i])
        faj[i] = calcular_faj(
            xi, cnu, rp_a, a["edad_maxima"][i], a["saldo"][i], a["pcent"][i], rp0_i, criter, maxiter,
        )
    if sin_vector:
        warnings.warn(
            f"Para las siguientes observaciones ({len(sin_vector)}) se intentó utilizar un vector "
            f"inexistente: {' '.join(map(str, sin_vector[:20]))}",
            AdvertenciaCNU,
            stacklevel=2,
        )
    return faj


__all__ = ["faj_funcion_objetivo", "calcular_faj", "faj_afiliado", "faj_afiliado_vec"]

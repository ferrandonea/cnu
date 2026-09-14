"""Factor de Ajuste (FAJ) para Retiros Programados.

Equivale a ``cnu_faj.mata`` (``cnu_faj_fun_obj``, ``cnu_faj`` y ``cnu_faj_vec``)
y a los comandos ``cnu_faji`` (escalar) y ``cnu_faj`` (vectorial) de Stata.

**Derogado.** La Ley N 21.419 elimino el Factor de Ajuste del retiro
programado a contar del 1 de febrero de 2022 (Capitulo V del Libro III del
Compendio de Normas, derogado). Las funciones se conservan para reproducir
calculos historicos: cuando la fecha de calculo (``fsiniestro`` o, en su
defecto, el 31 de diciembre de ``agno_actual``, igual que la resolucion de
tablas) es igual o posterior a :data:`DEROGACION_FAJ`, emiten una
:class:`cnu.AdvertenciaCNU` y devuelven el valor de todos modos.
"""

from __future__ import annotations

import math
import warnings

import numpy as np

from . import core
from .core import AGNO_VECTOR, EDAD_MAXIMA, EDAD_MINIMA, TABLA_AFILIADO, TABLA_BENEFICIARIO
from .tablas import fecha_fin_de_agno
from .vectorial import AdvertenciaCNU

EDAD_MAXIMA_FAJ = 98
PCENT = 0.3
CRITERIO = 1e-6
MAXITER = 100

# Ley N 21.419: el FAJ deja de existir para el retiro programado desde esta
# fecha (YYYYMMDD). Ver el docstring del modulo.
DEROGACION_FAJ = 20220201

MENSAJE_FAJ_DEROGADO = (
    "El Factor de Ajuste (FAJ) esta derogado: la Ley N 21.419 lo elimino del retiro programado "
    "a contar del 1 de febrero de 2022. El resultado solo sirve para reproducir calculos historicos."
)


def fecha_calculo_faj(fsiniestro: int = 0, agno_actual: int | None = None) -> int:
    """Fecha ``YYYYMMDD`` a la que se evalua la vigencia del FAJ.

    Igual que la resolucion de tablas: ``fsiniestro`` si es distinto de 0 o, en
    su defecto, el 31 de diciembre de ``agno_actual`` (por defecto, el agno en
    curso).
    """
    if fsiniestro is not None and not core._es_missing(fsiniestro) and int(fsiniestro):
        return int(fsiniestro)
    return fecha_fin_de_agno(core._agno(agno_actual))


def faj_derogado(fsiniestro: int = 0, agno_actual: int | None = None) -> bool:
    """``True`` si a la fecha de calculo el FAJ ya no existe (ver :data:`DEROGACION_FAJ`)."""
    return fecha_calculo_faj(fsiniestro, agno_actual) >= DEROGACION_FAJ


def _advertir_faj_derogado(n_filas: int | None = None, stacklevel: int = 3) -> None:
    detalle = "" if n_filas is None else f" ({n_filas} observaciones con fecha de calculo posterior a la derogacion)"
    warnings.warn(MENSAJE_FAJ_DEROGADO + detalle, AdvertenciaCNU, stacklevel=stacklevel)


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
    rp: float | None = None,
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

    La tasa de capitalizacion del saldo sigue la regla unica de
    :func:`cnu.core.tasas_por_periodo`: ``rp`` (TITRP), ``agno_vector``
    explicito o, sin ellos, el vector del agno de un ``fsiniestro`` anterior a
    2014; sin tasa determinable lanza ``ValueError``. No hay ``rp`` por
    defecto.

    Para la trayectoria del CNU, si ``agno_vector`` se entrega explicitamente
    se usa ese vector (como el comando de Stata; reproduce los valores
    historicos del FAJ). En caso contrario se usa la misma tasa constante
    ``rp`` de la capitalizacion, igual que :func:`faj_afiliado_vec`.

    **FAJ derogado desde el 1 de febrero de 2022 (Ley N 21.419).** Si la fecha
    de calculo (``fsiniestro`` o el 31 de diciembre de ``agno_actual``) es
    igual o posterior a :data:`DEROGACION_FAJ` se emite una
    :class:`cnu.AdvertenciaCNU`; el valor se calcula igual y solo sirve para
    reproducir calculos historicos.

    Las tablas ``tabla`` (afiliado, sexo ``cot_mujer``) y ``tabla_benef``
    (beneficiario, sexo ``cony_mujer``), por defecto ``"vigente"``, se
    resuelven una sola vez al inicio (``fsiniestro`` o el 31 de diciembre de
    ``agno_actual``) y se usan en toda la trayectoria del CNU
    (:func:`cnu.proyectar_cnu`).
    """
    from .proyeccion import proyectar_cnu  # importacion diferida (ciclo)

    x = core.edad_entera(x)
    rp_a = core.tasas_por_periodo(agno_vector, None, rp, dir_vectores, fsiniestro)
    # Con agno_vector explicito la trayectoria usa el vector (rp=None en cada
    # periodo); sin el, la misma tasa por periodo que la capitalizacion.
    rp_cnu = None if core._agno_vector_explicito(agno_vector) else rp_a
    cnu = proyectar_cnu(
        x, y, cot_mujer, cony_mujer, tabla, tabla_benef, agno_vector, agno_actual,
        None, rp_cnu, fsiniestro, dir_tablas, dir_vectores,
    )
    if faj_derogado(fsiniestro, agno_actual):
        _advertir_faj_derogado()
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

    La tasa de cada fila sigue la regla unica de
    :func:`cnu.core.tasas_por_periodo` (``rp``, ``agno_vector`` o
    ``fsiniestro`` anterior a 2014 de esa observacion) y se usa tanto para
    capitalizar el saldo como para la trayectoria del CNU: la tasa del periodo
    ``j`` se aplica como tasa constante al CNU del periodo ``j``
    (comportamiento heredado de ``cnu_faj_vec``). Las filas sin tasa
    determinable o con vector inexistente quedan en ``nan`` y se acumulan en
    una :class:`cnu.AdvertenciaCNU` con el motivo.

    Las tablas (por defecto ``"vigente"``) se resuelven por fila, con el rol,
    el sexo y la fecha de cada observacion, al inicio de su trayectoria.

    **FAJ derogado desde el 1 de febrero de 2022 (Ley N 21.419).** Si alguna
    fila tiene fecha de calculo (``fsiniestro`` o el 31 de diciembre de su
    ``agno_actual``) igual o posterior a :data:`DEROGACION_FAJ` se emite una
    sola :class:`cnu.AdvertenciaCNU` por llamada; los valores se calculan
    igual y solo sirven para reproducir calculos historicos.
    """
    from .proyeccion import proyectar_cnu  # importacion diferida (ciclo)
    from .vectorial import _advertir, _motivo_sin_tasa, _opcional, _preparar

    x = np.atleast_1d(np.asarray(x, dtype=float))
    n = len(x)
    a = _preparar(n, y=y, cot_mujer=cot_mujer, cony_mujer=cony_mujer, tabla=tabla, tabla_benef=tabla_benef,
                  agno_vector=agno_vector, agno_actual=agno_actual, rp=rp, fsiniestro=fsiniestro,
                  edad_maxima=edad_maxima, saldo=saldo, pcent=pcent, rp0=rp0, incluir=incluir)
    faj = np.full(n, np.nan)
    errores: dict[str, list[int]] = {"sin_tasa": [], "vector": []}
    derogadas = 0
    for i in range(n):
        if not a["incluir"][i] or math.isnan(x[i]):
            continue
        xi = core.edad_entera(x[i])
        if xi < EDAD_MINIMA or xi > EDAD_MAXIMA:
            continue
        rp_i = _opcional(a["rp"][i])
        motivo = _motivo_sin_tasa(a, i, None, rp_i, dir_vectores)
        if motivo is not None:
            errores[motivo].append(i)
            continue
        agno_vec = None if math.isnan(a["agno_vector"][i]) else int(a["agno_vector"][i])
        rp_a = core.tasas_por_periodo(agno_vec, None, rp_i, dir_vectores, int(a["fsiniestro"][i]))
        yi = None if math.isnan(a["y"][i]) else core.edad_entera(a["y"][i])
        agno_act = None if math.isnan(a["agno_actual"][i]) else int(a["agno_actual"][i])
        derogadas += faj_derogado(int(a["fsiniestro"][i]), agno_act)
        cnu = proyectar_cnu(
            xi, yi, bool(a["cot_mujer"][i]), bool(a["cony_mujer"][i]), a["tabla"][i], a["tabla_benef"][i],
            agno_vec, agno_act, None, rp_a, int(a["fsiniestro"][i]), dir_tablas, dir_vectores,
        )
        rp0_i = None if math.isnan(a["rp0"][i]) else float(a["rp0"][i])
        faj[i] = calcular_faj(
            xi, cnu, rp_a, a["edad_maxima"][i], a["saldo"][i], a["pcent"][i], rp0_i, criter, maxiter,
        )
    _advertir(errores, {
        "sin_tasa": "Las siguientes observaciones quedan sin tasa: desde 2014 se requiere rp"
                    " (o agno_vector o fsiniestro anterior a 2014)",
        "vector": "Para las siguientes observaciones se intentó utilizar un vector inexistente",
    })
    if derogadas:
        _advertir_faj_derogado(derogadas)
    return faj


__all__ = [
    "DEROGACION_FAJ", "faj_funcion_objetivo", "calcular_faj", "faj_afiliado", "faj_afiliado_vec",
    "faj_derogado", "fecha_calculo_faj",
]

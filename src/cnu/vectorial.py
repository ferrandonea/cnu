"""Versiones vectoriales de las formulas de CNU (una observacion por fila).

Equivalen a los comandos ``cnu_afil``, ``cnu_cnyg_s_h`` y ``cnu_sobr_cnyg_s_h``
de Stata: cada argumento puede ser un escalar (se aplica a todas las filas) o
un arreglo de largo ``N``. Las filas que no se pueden calcular (edad fuera de
[20, 110], vector de tasas inexistente, o excluidas con ``incluir``) quedan en
``nan`` y se emite un :class:`AdvertenciaCNU` con el detalle.

Las tablas de mortalidad (``tabla``, ``tabla_benef``; por defecto
``"vigente"``) se resuelven fila a fila segun el rol, el sexo y la fecha de
cada observacion: ``fsiniestro`` si es distinto de 0 o, en su defecto, el 31
de diciembre de su ``agno_actual`` (ver :func:`cnu.core.tabla_mortalidad`).
"""

from __future__ import annotations

import math
import warnings
from collections.abc import Callable

import numpy as np

from . import core
from .core import AGNO_VECTOR, EDAD_MAXIMA, EDAD_MINIMA, TABLA_AFILIADO, TABLA_BENEFICIARIO

MAX_LISTADO = 20


class AdvertenciaCNU(UserWarning):
    """Advierte de observaciones para las que no fue posible calcular el CNU."""


def _columna(valor, n: int, dtype=None) -> np.ndarray:
    """Expande ``valor`` (escalar o secuencia) a un arreglo de largo ``n``."""
    if valor is None:
        arr = np.full(n, np.nan)
    else:
        arr = np.asarray(valor, dtype=dtype)
        if arr.ndim == 0:
            arr = np.full(n, arr.item(), dtype=arr.dtype)
        elif arr.shape != (n,):
            raise ValueError(f"Se esperaba un arreglo de largo {n}, se recibio uno de forma {arr.shape}")
    if dtype is None and arr.dtype.kind in "iub":
        arr = arr.astype(float)
    return arr


def _opcional(v):
    """``nan``/``None`` -> ``None`` (tasa no especificada)."""
    if v is None:
        return None
    v = float(v)
    return None if math.isnan(v) else v


def _entero_o_nan(v):
    return None if v is None or (isinstance(v, float) and math.isnan(v)) else int(v)


def _advertir(errores: dict[str, list[int]], mensajes: dict[str, str]) -> None:
    lineas = []
    k = 0
    for clave, texto in mensajes.items():
        idx = errores.get(clave) or []
        if not idx:
            continue
        k += 1
        muestra = " ".join(str(i) for i in idx[:MAX_LISTADO])
        sufijo = "..." if len(idx) > MAX_LISTADO else ""
        lineas.append(f" ({k}) {texto} ({len(idx)}): {muestra}{sufijo}")
    if lineas:
        warnings.warn(
            "ADVERTENCIA (indices base 0):\n" + "\n".join(lineas)
            + "\nPor lo que no fue posible calcular CNU para estas.",
            AdvertenciaCNU,
            stacklevel=3,
        )


def _sin_tasas(a: dict[str, np.ndarray], j: int, rv, rp, dir_vectores) -> bool:
    """``True`` si :func:`cnu.core.tasas_por_periodo` no puede resolver la fila ``j``."""
    return core.tasas_por_periodo(
        a["agno_vector"][j], rv, rp, dir_vectores, int(a["fsiniestro"][j]), estricto=False
    ) is None


def cnu_afiliado_vec(
    x,
    mujer=False,
    tabla=TABLA_AFILIADO,
    agno_vector=AGNO_VECTOR,
    agno_actual=None,
    rv=None,
    rp=None,
    fsiniestro=0,
    incluir=None,
    dir_tablas=None,
    dir_vectores=None,
) -> np.ndarray:
    """CNU de afiliado para varias observaciones (equivale a ``cnu_afil``).

    Vease :func:`cnu.core.cnu_afiliado` para el significado de cada argumento.
    ``rv``/``rp`` aceptan ``nan`` por fila para indicar "no especificado".
    ``tabla`` (por defecto ``"vigente"``) se resuelve por fila con el sexo
    ``mujer`` y la fecha (``fsiniestro`` o fin de ``agno_actual``) de esa fila.
    """
    x = np.atleast_1d(np.asarray(x, dtype=float))
    n = len(x)
    a = _preparar(n, mujer=mujer, tabla=tabla, agno_vector=agno_vector, agno_actual=agno_actual,
                  rv=rv, rp=rp, fsiniestro=fsiniestro, incluir=incluir)
    modo_rv = rv is not None
    modo_rp = rp is not None
    cnu = np.full(n, np.nan)
    errores: dict[str, list[int]] = {"menor_20": [], "mayor_110": [], "vector": []}
    for j in range(n):
        if not a["incluir"][j] or math.isnan(x[j]):
            continue
        edad = core.edad_entera(x[j])
        rv_j = _opcional(a["rv"][j]) if modo_rv else None
        rp_j = _opcional(a["rp"][j]) if modo_rp else None
        if edad < EDAD_MINIMA:
            errores["menor_20"].append(j)
        elif edad > EDAD_MAXIMA:
            errores["mayor_110"].append(j)
        elif _sin_tasas(a, j, rv_j, rp_j, dir_vectores):
            errores["vector"].append(j)
        elif modo_rv and rv_j is None:
            continue  # RV con tasa faltante en esta fila -> nan
        else:
            cnu[j] = core.cnu_afiliado(
                edad, bool(a["mujer"][j]), a["tabla"][j], int(a["agno_vector"][j]),
                _entero_o_nan(a["agno_actual"][j]), rv_j, rp_j, int(a["fsiniestro"][j]),
                False, dir_tablas, dir_vectores,
            )
    _advertir(errores, {
        "menor_20": "Los siguientes cotizantes tienen menos de 20 años",
        "mayor_110": "Los siguientes cotizantes tienen más de 110 años",
        "vector": "Para las siguientes observaciones se intentó utilizar un vector inexistente",
    })
    return cnu


def cnu_conyuge_vec(
    x,
    y,
    cot_mujer=False,
    cony_mujer=False,
    tabla=TABLA_AFILIADO,
    tabla_benef=TABLA_BENEFICIARIO,
    agno_vector=AGNO_VECTOR,
    agno_actual=None,
    rv=None,
    rp=None,
    fsiniestro=0,
    incluir=None,
    dir_tablas=None,
    dir_vectores=None,
) -> np.ndarray:
    """CNU de conyuge sin hijos para varias observaciones (equivale a ``cnu_cnyg_s_h``).

    Nota: igual que el comando vectorial de Stata, ``cony_mujer`` es ``False``
    por defecto (el comando escalar usaba ``True``). ``tabla`` (rol afiliado,
    sexo ``cot_mujer``) y ``tabla_benef`` (rol beneficiario, sexo
    ``cony_mujer``), por defecto ``"vigente"``, se resuelven por fila.
    """
    x = np.atleast_1d(np.asarray(x, dtype=float))
    n = len(x)
    y = _columna(y, n)
    a = _preparar(n, cot_mujer=cot_mujer, cony_mujer=cony_mujer, tabla=tabla, tabla_benef=tabla_benef,
                  agno_vector=agno_vector, agno_actual=agno_actual, rv=rv, rp=rp,
                  fsiniestro=fsiniestro, incluir=incluir)
    modo_rv = rv is not None
    modo_rp = rp is not None
    cnu = np.full(n, np.nan)
    errores: dict[str, list[int]] = {
        "menor_20_cot": [], "menor_20_cony": [], "mayor_110_cot": [], "mayor_110_cony": [], "vector": [],
    }
    for j in range(n):
        if not a["incluir"][j] or math.isnan(x[j]) or math.isnan(y[j]):
            continue
        ex, ey = core.edad_entera(x[j]), core.edad_entera(y[j])
        rv_j = _opcional(a["rv"][j]) if modo_rv else None
        rp_j = _opcional(a["rp"][j]) if modo_rp else None
        if ex < EDAD_MINIMA:
            errores["menor_20_cot"].append(j)
        elif ey < EDAD_MINIMA:
            errores["menor_20_cony"].append(j)
        elif ex > EDAD_MAXIMA:
            errores["mayor_110_cot"].append(j)
        elif _sin_tasas(a, j, rv_j, rp_j, dir_vectores):
            errores["vector"].append(j)
        elif ey > EDAD_MAXIMA:
            errores["mayor_110_cony"].append(j)
        elif modo_rv and rv_j is None:
            continue
        else:
            cnu[j] = core.cnu_conyuge(
                ex, ey, bool(a["cot_mujer"][j]), bool(a["cony_mujer"][j]), a["tabla"][j], a["tabla_benef"][j],
                int(a["agno_vector"][j]), _entero_o_nan(a["agno_actual"][j]), rv_j, rp_j,
                int(a["fsiniestro"][j]), False, dir_tablas, dir_vectores,
            )
    _advertir(errores, {
        "menor_20_cot": "Los siguientes cotizantes tienen menos de 20 años",
        "menor_20_cony": "Los siguientes cónyuges tienen menos de 20 años",
        "mayor_110_cot": "Los siguientes cotizantes tienen más de 110 años",
        "mayor_110_cony": "Los siguientes cónyuges tienen más de 110 años",
        "vector": "Para las siguientes observaciones se intentó utilizar un vector inexistente",
    })
    return cnu


def cnu_sobrevivencia_conyuge_vec(
    y,
    mujer=False,
    tabla_benef=TABLA_BENEFICIARIO,
    agno_vector=AGNO_VECTOR,
    agno_actual=None,
    rv=None,
    rp=None,
    fsiniestro=0,
    incluir=None,
    dir_tablas=None,
    dir_vectores=None,
) -> np.ndarray:
    """CNU de sobrevivencia para conyuge sin hijos, varias observaciones
    (equivale a ``cnu_sobr_cnyg_s_h``).

    ``tabla_benef`` (rol beneficiario, sexo ``mujer``; por defecto
    ``"vigente"``) se resuelve por fila con la fecha de esa fila.
    """
    y = np.atleast_1d(np.asarray(y, dtype=float))
    n = len(y)
    a = _preparar(n, mujer=mujer, tabla_benef=tabla_benef, agno_vector=agno_vector, agno_actual=agno_actual,
                  rv=rv, rp=rp, fsiniestro=fsiniestro, incluir=incluir)
    modo_rv = rv is not None
    modo_rp = rp is not None
    cnu = np.full(n, np.nan)
    errores: dict[str, list[int]] = {"menor_20": [], "mayor_110": [], "vector": []}
    for j in range(n):
        if not a["incluir"][j] or math.isnan(y[j]):
            continue
        edad = core.edad_entera(y[j])
        rv_j = _opcional(a["rv"][j]) if modo_rv else None
        rp_j = _opcional(a["rp"][j]) if modo_rp else None
        if edad < EDAD_MINIMA:
            errores["menor_20"].append(j)
        elif edad > EDAD_MAXIMA:
            errores["mayor_110"].append(j)
        elif _sin_tasas(a, j, rv_j, rp_j, dir_vectores):
            errores["vector"].append(j)
        elif modo_rv and rv_j is None:
            continue
        else:
            cnu[j] = core.cnu_sobrevivencia_conyuge(
                edad, bool(a["mujer"][j]), a["tabla_benef"][j], int(a["agno_vector"][j]),
                _entero_o_nan(a["agno_actual"][j]), rv_j, rp_j, int(a["fsiniestro"][j]),
                False, dir_tablas, dir_vectores,
            )
    _advertir(errores, {
        "menor_20": "Los siguientes cónyuges tienen menos de 20 años",
        "mayor_110": "Los siguientes cónyuges tienen más de 110 años",
        "vector": "Para las siguientes observaciones se intentó utilizar un vector inexistente",
    })
    return cnu


def _preparar(n: int, **kw) -> dict[str, np.ndarray]:
    """Expande todos los argumentos a columnas de largo ``n``."""
    out = {}
    for k, v in kw.items():
        if k in ("tabla", "tabla_benef"):
            out[k] = _columna(v, n, dtype=object)
        elif k == "incluir":
            out[k] = np.ones(n, dtype=bool) if v is None else _columna(v, n, dtype=bool)
        elif k in ("mujer", "cot_mujer", "cony_mujer"):
            out[k] = _columna(v, n, dtype=bool)
        else:
            out[k] = _columna(v, n)
    return out


__all__: list[str] = [
    "AdvertenciaCNU",
    "cnu_afiliado_vec",
    "cnu_conyuge_vec",
    "cnu_sobrevivencia_conyuge_vec",
]

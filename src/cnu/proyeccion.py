"""Proyeccion del CNU y de la trayectoria de pension en Retiro Programado.

Equivale a ``cnu_proy_cnu`` y ``cnu_proy_pens`` (comando ``cnu_proy_pensi``).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from . import core
from .core import AGNO_VECTOR, EDAD_MAXIMA, EDAD_MINIMA, TABLA_AFILIADO, TABLA_BENEFICIARIO
from .faj import calcular_faj


def _por_fila(valor, n: int) -> list:
    """``None`` -> lista de ``None``; escalar -> repetido; arreglo -> por fila."""
    if valor is None:
        return [None] * n
    arr = np.asarray(valor, dtype=float)
    if arr.ndim == 0:
        v = float(arr)
        return [None if math.isnan(v) else v] * n
    if len(arr) < n:
        raise ValueError(f"Se requieren al menos {n} tasas, se entregaron {len(arr)}")
    return [None if math.isnan(v) else float(v) for v in arr[:n]]


def proyectar_cnu(
    x: int,
    y: int | None = None,
    cot_mujer: bool = False,
    cony_mujer: bool = True,
    tabla: str = TABLA_AFILIADO,
    tabla_benef: str = TABLA_BENEFICIARIO,
    agno_vector: int = AGNO_VECTOR,
    agno_actual: int | None = None,
    rv=None,
    rp=None,
    fsiniestro: int = 0,
    dir_tablas=None,
    dir_vectores=None,
) -> np.ndarray:
    """Trayectoria del CNU desde la edad ``x`` hasta los 110 años.

    El CNU del periodo ``j`` se calcula para la edad ``x + j`` en el año
    ``agno_actual + j`` (con ``y + j`` para el conyuge, si lo hay). Si el
    conyuge supera los 110 años su aporte es 0.

    ``rp`` y ``rv`` pueden ser ``None``, un escalar o un arreglo con una tasa
    por periodo proyectado (como en Mata, la tasa ``j`` se usa como tasa
    constante para el CNU del periodo ``j``). Si ``rv`` se entrega, el CNU es
    de Renta Vitalicia.
    """
    x = int(x)
    agno_actual = core._agno(agno_actual)
    n = EDAD_MAXIMA - x + 1
    xs = range(x, EDAD_MAXIMA + 1)
    agnos = range(agno_actual, agno_actual + n)
    rvs = _por_fila(rv, n)
    rps = _por_fila(rp, n)
    modo_rv = rv is not None

    cnu = np.full(n, np.nan)
    for j, (ex, agno) in enumerate(zip(xs, agnos)):
        if ex < EDAD_MINIMA:
            continue
        if modo_rv and rvs[j] is None:
            continue
        cnu[j] = core.cnu_afiliado(
            ex, cot_mujer, tabla, agno_vector, agno, rvs[j], None if modo_rv else rps[j],
            fsiniestro, False, dir_tablas, dir_vectores,
        )
        if y is not None and not core._es_missing(y):
            ey = int(y) + j
            if EDAD_MINIMA <= ey <= EDAD_MAXIMA:
                cnu[j] += core.cnu_conyuge(
                    ex, ey, cot_mujer, cony_mujer, tabla, tabla_benef, agno_vector, agno,
                    rvs[j], None if modo_rv else rps[j], fsiniestro, False, dir_tablas, dir_vectores,
                )
    return cnu


@dataclass
class ProyeccionPension:
    """Trayectoria de pension en Retiro Programado.

    ``faj`` y ``saldo_faj`` solo se llenan cuando la proyeccion incluye Factor
    de Ajuste.
    """

    edad: np.ndarray
    saldo: np.ndarray
    pension: np.ndarray
    faj: float | None = None
    saldo_faj: np.ndarray | None = None
    descripcion: str = ""

    @property
    def con_faj(self) -> bool:
        return self.faj is not None

    def columnas(self) -> dict[str, np.ndarray]:
        if self.con_faj:
            return {
                "edad": self.edad,
                "saldo": self.saldo,
                "faj": np.full(len(self.edad), self.faj),
                "saldo_faj": self.saldo_faj,
                "pension": self.pension,
            }
        return {"edad": self.edad, "saldo": self.saldo, "pension": self.pension}

    def como_matriz(self) -> np.ndarray:
        """Matriz con las mismas columnas que ``r(pens)`` en Stata."""
        return np.column_stack(list(self.columnas().values()))

    def to_dataframe(self):
        """Devuelve un ``pandas.DataFrame`` (requiere pandas instalado)."""
        import pandas as pd  # importacion diferida: pandas es opcional

        return pd.DataFrame(self.columnas())


def proyectar_pension(
    x: int,
    y: int | None = None,
    saldo: float = 1.0,
    cot_mujer: bool = False,
    cony_mujer: bool = True,
    tabla: str = TABLA_AFILIADO,
    tabla_benef: str = TABLA_BENEFICIARIO,
    agno_vector: int = AGNO_VECTOR,
    agno_actual: int | None = None,
    rp: float | None = 0.03,
    fsiniestro: int = 0,
    faj: bool = False,
    edad_maxima: int = 98,
    pcent: float = 0.3,
    rp0: float | None = None,
    criter: float = 1e-6,
    maxiter: int = 100,
    dir_tablas=None,
    dir_vectores=None,
) -> ProyeccionPension:
    """Proyecta saldo y pension de Retiro Programado desde la edad ``x`` (``cnu_proy_pensi``).

    :param saldo: saldo al momento del retiro (1 = resultados como fraccion del saldo).
    :param rp: tasa de retiro programado; ``None`` usa el vector ``agno_vector``.
    :param faj: si ``True``, la pension incluye Factor de Ajuste (ver :mod:`cnu.faj`).
    :param edad_maxima, pcent, rp0, criter, maxiter: parametros del FAJ.
    """
    x = int(x)
    agno_actual = core._agno(agno_actual)
    if saldo == 0:
        saldo = 1.0
    n = EDAD_MAXIMA - x + 1
    cnu = proyectar_cnu(
        x, y, cot_mujer, cony_mujer, tabla, tabla_benef, agno_vector, agno_actual,
        None, rp, fsiniestro, dir_tablas, dir_vectores,
    )
    tasas = core.tasas_por_periodo(agno_vector, None, rp, dir_vectores)
    edades = np.arange(x, EDAD_MAXIMA + 1, dtype=float)

    quien = "afiliado soltero" if y is None else "afiliado con conyuge"
    tablas = tabla if y is None else f"{tabla} {tabla_benef}"
    tasa = f"vector {agno_vector}" if rp is None else f"tasa {rp:g}"
    sufijo = " con FAJ" if faj else ""
    descripcion = f"Trayectoria de pension{sufijo} para {quien} (tabla {tablas}) {tasa} en {agno_actual}."

    pens = np.full(n, np.nan)
    saldos = np.full(n, np.nan)

    if not faj:
        pens[0] = saldo / cnu[0]
        saldos[0] = (saldo - pens[0]) * (1 + tasas[0])
        for i in range(1, n):
            pens[i] = saldos[i - 1] / cnu[i]
            saldos[i] = max(0.0, (saldos[i - 1] - pens[i]) * (1 + tasas[i]))
        return ProyeccionPension(edades, saldos, pens, descripcion=descripcion)

    f = calcular_faj(x, cnu, tasas, edad_maxima, saldo, pcent, rp0, criter, maxiter)

    pensfaj = pcent * saldo / cnu[0]
    saldofaj = np.zeros(n)
    fajactivo = False

    pens[0] = pensfaj / pcent * (1 - f)
    saldos[0] = (saldo - pens[0] - pens[0] / (1 - f) * f) * (1 + tasas[0])
    saldofaj[0] = pens[0] / (1 - f) * f * (1 + tasas[0])
    for i in range(1, n):
        if not fajactivo:
            pens[i] = saldos[i - 1] / cnu[i] * (1 - f)
            # Mientras la pension supere la pension FAJ, se sigue acumulando reserva.
            if pens[i] > pensfaj:
                saldofaj[i] = (saldofaj[i - 1] + saldos[i - 1] / cnu[i] * f) * (1 + tasas[i])
                saldos[i] = (saldos[i - 1] - saldos[i - 1] / cnu[i]) * (1 + tasas[i])
                continue
            fajactivo = True

        # Pension y saldos segun FAJ
        if saldofaj[i - 1] - (pensfaj - saldos[i - 1] / cnu[i]) < 0:
            pens[i] = saldos[i - 1] / cnu[i]
            saldos[i] = (saldos[i - 1] - saldos[i - 1] / cnu[i]) * (1 + tasas[i])
            continue

        pens[i] = pensfaj
        saldos[i] = (saldos[i - 1] - saldos[i - 1] / cnu[i]) * (1 + tasas[i])
        saldofaj[i] = (saldofaj[i - 1] - (pensfaj - saldos[i - 1] / cnu[i])) * (1 + tasas[i])

    return ProyeccionPension(edades, saldos, pens, f, saldofaj, descripcion)


__all__ = ["ProyeccionPension", "proyectar_cnu", "proyectar_pension"]

"""Proyeccion del CNU y de la trayectoria de pension en Retiro Programado.

Equivale a ``cnu_proy_cnu`` y ``cnu_proy_pens`` (comando ``cnu_proy_pensi``).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from . import core
from .core import AGNO_VECTOR, EDAD_MAXIMA, EDAD_MINIMA, TABLA_AFILIADO, TABLA_BENEFICIARIO
from .faj import _advertir_faj_derogado, calcular_faj, faj_derogado, fecha_calculo_faj

# Ley N 21.735: desde esta fecha (YYYYMMDD) la pension de retiro programado no
# puede variar mas de :data:`BANDA_VARIACION` respecto de la anterior en los
# recalculos derivados de los ajustes de la TITRP (oficio de la SP del 17 de
# abril de 2025). Ver :func:`proyectar_pension`.
VIGENCIA_BANDA = 20250901
BANDA_VARIACION = 0.10


def banda_vigente(fsiniestro: int = 0, agno_actual: int | None = None) -> bool:
    """``True`` si a la fecha de calculo rige la banda del 10% (ver :data:`VIGENCIA_BANDA`).

    La fecha de calculo es la misma del FAJ y de las tablas: ``fsiniestro`` o,
    en su defecto, el 31 de diciembre de ``agno_actual``.
    """
    return fecha_calculo_faj(fsiniestro, agno_actual) >= VIGENCIA_BANDA


def _acotar(libre: float, anterior: float, disponible: float) -> tuple[float, bool]:
    """Pension del periodo con la banda: ``[0,9; 1,1] x anterior`` y nunca mas que el saldo disponible.

    Devuelve la pension acotada y si la banda actuo (la pension libre estaba
    fuera de la banda).
    """
    inf, sup = (1 - BANDA_VARIACION) * anterior, (1 + BANDA_VARIACION) * anterior
    acotada = min(max(libre, inf), sup)
    pagada = min(acotada, disponible)
    return pagada, pagada != libre


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


def _tablas_resueltas(y, cot_mujer, cony_mujer, tabla, tabla_benef, agno_actual, fsiniestro, dir_tablas):
    """Nombres explicitos de las tablas del afiliado y del conyuge (si lo hay)."""
    tabla = core.nombre_tabla_resuelta(tabla, core.ROL_AFILIADO, cot_mujer, fsiniestro, agno_actual, dir_tablas)
    if y is not None and not core._es_missing(y):
        tabla_benef = core.nombre_tabla_resuelta(
            tabla_benef, core.ROL_BENEFICIARIO, cony_mujer, fsiniestro, agno_actual, dir_tablas
        )
    return tabla, tabla_benef


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
    de Renta Vitalicia. Cada CNU de la trayectoria aplica la regla unica de
    :func:`cnu.core.tasas_por_periodo`: sin ``rv`` ni ``rp`` se usa
    ``agno_vector`` explicito o el vector del agno de un ``fsiniestro``
    anterior a 2014; en otro caso lanza ``ValueError`` (TITRP en ``rp``).

    Las tablas se resuelven una sola vez, al inicio de la proyeccion
    (``fsiniestro`` o, con ``"vigente"``, el 31 de diciembre de
    ``agno_actual``), y se usan en toda la trayectoria.
    """
    x = core.edad_entera(x)
    agno_actual = core._agno(agno_actual)
    tabla, tabla_benef = _tablas_resueltas(
        y, cot_mujer, cony_mujer, tabla, tabla_benef, agno_actual, fsiniestro, dir_tablas
    )
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
            ey = core.edad_entera(y) + j
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
    de Ajuste; ``acotado`` (un booleano por periodo: ``True`` donde la banda del
    10% cambio la pension) solo cuando se aplico la banda.
    """

    edad: np.ndarray
    saldo: np.ndarray
    pension: np.ndarray
    faj: float | None = None
    saldo_faj: np.ndarray | None = None
    descripcion: str = ""
    acotado: np.ndarray | None = None

    @property
    def con_faj(self) -> bool:
        return self.faj is not None

    @property
    def con_banda(self) -> bool:
        return self.acotado is not None

    def columnas(self) -> dict[str, np.ndarray]:
        cols = {"edad": self.edad, "saldo": self.saldo}
        if self.con_faj:
            cols["faj"] = np.full(len(self.edad), self.faj)
            cols["saldo_faj"] = self.saldo_faj
        cols["pension"] = self.pension
        if self.con_banda:
            cols["acotado"] = self.acotado.astype(int)
        return cols

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
    rp: float | None = None,
    fsiniestro: int = 0,
    faj: bool = False,
    banda: bool | None = None,
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
    :param tabla, tabla_benef: tablas del afiliado (sexo ``cot_mujer``) y del
        conyuge (sexo ``cony_mujer``); por defecto ``"vigente"``, resueltas
        una sola vez al inicio (``fsiniestro`` o el 31 de diciembre de
        ``agno_actual``) como en :func:`proyectar_cnu`.
    :param rp: tasa unica de retiro programado (TITRP). Sin ``rp`` rige la
        regla de :func:`cnu.core.tasas_por_periodo`: ``agno_vector`` explicito
        o el vector del agno de un ``fsiniestro`` anterior a 2014; en otro
        caso ``ValueError``. No hay tasa por defecto.
    :param faj: si ``True``, la pension incluye Factor de Ajuste (ver
        :mod:`cnu.faj`). **El FAJ esta derogado desde el 1 de febrero de 2022
        (Ley N 21.419):** con ``faj=True`` y fecha de calculo (``fsiniestro`` o
        el 31 de diciembre de ``agno_actual``) igual o posterior a
        :data:`cnu.faj.DEROGACION_FAJ` se emite una :class:`cnu.AdvertenciaCNU`
        y la proyeccion se calcula igual, solo para reproducir calculos
        historicos.
    :param banda: banda de variacion maxima del 10% de la Ley N 21.735
        (oficio de la SP del 17 de abril de 2025). ``None`` (por defecto): se
        aplica si la fecha de calculo (``fsiniestro`` o el 31 de diciembre de
        ``agno_actual``) es igual o posterior a :data:`VIGENCIA_BANDA`
        (20250901); ``True`` y ``False`` la fuerzan o la desactivan. Con la
        banda, la pension de cada periodo ``j >= 1`` queda en
        ``[0,9; 1,1] x pension(j - 1)`` (la primera pension no cambia), el
        saldo se descuenta con la pension efectivamente pagada y
        ``ProyeccionPension.acotado`` marca los periodos donde la banda actuo.
        La pension nunca supera el saldo disponible (si la banda exige mas de
        lo que queda, se paga el saldo y la cuenta se agota). Simplificacion:
        la norma regula los ajustes trimestrales de la TITRP y esta proyeccion
        es anual, por lo que la banda se aplica entre periodos anuales
        consecutivos; los recalculos extraordinarios, excluidos de la banda
        por la ley, no forman parte de la proyeccion.
    :param edad_maxima, pcent, rp0, criter, maxiter: parametros del FAJ.
    """
    x = core.edad_entera(x)
    agno_actual = core._agno(agno_actual)
    tabla, tabla_benef = _tablas_resueltas(
        y, cot_mujer, cony_mujer, tabla, tabla_benef, agno_actual, fsiniestro, dir_tablas
    )
    if saldo == 0:
        saldo = 1.0
    n = EDAD_MAXIMA - x + 1
    tasas = core.tasas_por_periodo(agno_vector, None, rp, dir_vectores, fsiniestro)
    cnu = proyectar_cnu(
        x, y, cot_mujer, cony_mujer, tabla, tabla_benef, agno_vector, agno_actual,
        None, rp, fsiniestro, dir_tablas, dir_vectores,
    )
    edades = np.arange(x, EDAD_MAXIMA + 1, dtype=float)

    quien = "afiliado soltero" if y is None else "afiliado con conyuge"
    tablas = tabla if y is None else f"{tabla} {tabla_benef}"
    tasa = f"vector {core.agno_vector_efectivo(agno_vector, fsiniestro)}" if rp is None else f"tasa {rp * 100:g}%"
    if banda is None:
        banda = banda_vigente(fsiniestro, agno_actual)
    extras = [s for s, con in (("FAJ", faj), ("banda 10%", banda)) if con]
    sufijo = " con " + " y ".join(extras) if extras else ""
    descripcion = f"Trayectoria de pension{sufijo} para {quien} (tabla {tablas}) {tasa} en {agno_actual}."

    pens = np.full(n, np.nan)
    saldos = np.full(n, np.nan)
    acotado = np.zeros(n, dtype=bool) if banda else None

    if not faj:
        pens[0] = saldo / cnu[0]
        saldos[0] = (saldo - pens[0]) * (1 + tasas[0])
        for i in range(1, n):
            pens[i] = saldos[i - 1] / cnu[i]
            if banda:
                pens[i], acotado[i] = _acotar(pens[i], pens[i - 1], saldos[i - 1])
            saldos[i] = max(0.0, (saldos[i - 1] - pens[i]) * (1 + tasas[i]))
        return ProyeccionPension(edades, saldos, pens, descripcion=descripcion, acotado=acotado)

    if faj_derogado(fsiniestro, agno_actual):
        _advertir_faj_derogado()
    f = calcular_faj(x, cnu, tasas, edad_maxima, saldo, pcent, rp0, criter, maxiter)

    pensfaj = pcent * saldo / cnu[0]
    saldofaj = np.zeros(n)
    fajactivo = False

    pens[0] = pensfaj / pcent * (1 - f)
    saldos[0] = (saldo - pens[0] - pens[0] / (1 - f) * f) * (1 + tasas[0])
    saldofaj[0] = pens[0] / (1 - f) * f * (1 + tasas[0])
    for i in range(1, n):
        libre = saldos[i - 1] / cnu[i]
        if not fajactivo:
            pens[i] = libre * (1 - f)
            # Mientras la pension supere la pension FAJ, se sigue acumulando reserva.
            if pens[i] > pensfaj:
                saldofaj[i] = (saldofaj[i - 1] + libre * f) * (1 + tasas[i])
                saldos[i] = (saldos[i - 1] - libre) * (1 + tasas[i])
            else:
                fajactivo = True
        if fajactivo:
            # Pension y saldos segun FAJ
            if saldofaj[i - 1] - (pensfaj - libre) < 0:
                pens[i] = libre
                saldos[i] = (saldos[i - 1] - libre) * (1 + tasas[i])
            else:
                pens[i] = pensfaj
                saldos[i] = (saldos[i - 1] - libre) * (1 + tasas[i])
                saldofaj[i] = (saldofaj[i - 1] - (pensfaj - libre)) * (1 + tasas[i])
        if banda:
            # La banda actua sobre la pension pagada; la diferencia queda en (o sale de) la cuenta.
            pagada, acotado[i] = _acotar(pens[i], pens[i - 1], saldos[i - 1] + saldofaj[i - 1])
            saldos[i] = max(0.0, saldos[i] + (pens[i] - pagada) * (1 + tasas[i]))
            pens[i] = pagada

    return ProyeccionPension(edades, saldos, pens, f, saldofaj, descripcion, acotado)


__all__ = ["BANDA_VARIACION", "ProyeccionPension", "VIGENCIA_BANDA", "banda_vigente", "proyectar_cnu", "proyectar_pension"]

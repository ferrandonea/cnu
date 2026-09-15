"""Formulas escalares del Capital Necesario Unitario (CNU).

Equivalentes a las rutinas Mata ``cnu_2_1`` (afiliado), ``cnu_2_2`` (conyuge
sin hijos) y ``cnu_1_1`` (sobrevivencia para conyuge sin hijos), segun el
Anexo N 7 del Compendio de Normas de la Superintendencia de Pensiones, mas
las formulas del hijo no invalido (:func:`cnu_hijo`, letra e del punto 2, y
:func:`cnu_sobrevivencia_hijo`, letra d del punto 1) y del hijo invalido total
o parcial (:func:`cnu_hijo_invalido`, letra f del punto 2, y
:func:`cnu_sobrevivencia_hijo_invalido`, letra e del punto 1) y del conyuge
con hijos con derecho a pension (:func:`cnu_conyuge_con_hijos`, letras c y d
del punto 2, y :func:`cnu_sobrevivencia_conyuge_con_hijos`, letras b y c del
punto 1), de la madre o el padre de hijos de filiacion no matrimonial
(:func:`cnu_madre_padre`, letras i, j y k del punto 2, y
:func:`cnu_sobrevivencia_madre_padre`, letras h, i y j del punto 1) y de cada
padre del afiliado (:func:`cnu_padres`, letra l del punto 2, y
:func:`cnu_sobrevivencia_padres`, letra k del punto 1), que no tienen rutina
Mata. El conviviente civil (Ley N 20.830) se
calcula con las funciones del conyuge, cuyas formulas son identicas
(``conviviente=True``). Todas se calculan sobre el nucleo comun :func:`anualidad`, que admite
las variantes del Anexo (limite de periodos, condicion de fallecimiento del
afiliado, ajuste temporal por pago mensual y porcentaje del articulo 58 del
D.L. N 3.500).

Seleccion de la tasa de descuento (ver :func:`tasas_por_periodo`):

* ``rv`` dado -> Renta Vitalicia con tasa constante ``rv``.
* ``rp`` dado -> Retiro Programado con tasa constante ``rp`` (la TITRP).
* ``agno_vector`` dado -> Retiro Programado con el vector de tasas de ese agno.
* ninguno y siniestro anterior al 1 de enero de 2014 -> vector del agno del
  siniestro.
* ninguno en cualquier otro caso -> error: desde 2014 rige la tasa unica
  trimestral de retiro programado (TITRP) que publica la SP y debe entregarse
  en ``rp``.
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
    existe_vector_tasas,
    genero_desde_bool,
    resolver_tabla,
)

EDAD_MINIMA = 20
EDAD_MAXIMA = 110
EDAD_MINIMA_HIJO = 0  # los hijos se calculan desde los 0 agnos
EDAD_LIMITE_HIJO = 24  # ``z`` del Anexo N 7: edad limite de los hijos no invalidos
AJUSTE_MENSUAL = 11 / 24  # descuento por pago mensual (11/24 de una anualidad)

# Porcentajes de pension de sobrevivencia del articulo 58 del D.L. N 3.500
# (citados en el Anexo N 7), como fraccion de la pension de referencia.
FRACCION_CONYUGE = 0.6  # conyuge o conviviente civil sin hijos con derecho a pension
FRACCION_CONYUGE_CON_HIJOS = 0.5  # conyuge o conviviente civil con hijos con derecho a pension
FRACCION_MADRE_PADRE = 0.36  # madre o padre de hijos de filiacion no matrimonial, sin hijos con derecho
FRACCION_MADRE_PADRE_CON_HIJOS = 0.30  # madre o padre de hijos de filiacion no matrimonial, con hijos con derecho
FRACCION_HIJO = 0.15  # cada hijo (no invalido, o invalido total)
FRACCION_HIJO_INVALIDO_PARCIAL = 0.11  # hijo invalido parcial desde los 24 agnos
FRACCION_PADRES = 0.5  # cada padre del afiliado, a falta de otros beneficiarios

# Por defecto se usa la tabla vigente para el rol, sexo y fecha de calculo
# (fecha del siniestro o, en su defecto, el 31 de diciembre de ``agno_actual``).
TABLA_AFILIADO = TABLA_VIGENTE
TABLA_BENEFICIARIO = TABLA_VIGENTE

# Sin tasa explicita no hay vector de tasas por defecto: desde el 1 de enero
# de 2014 rige la tasa unica trimestral de retiro programado (TITRP) que
# publica la Superintendencia de Pensiones y debe entregarse en ``rp``. Solo
# los siniestros anteriores a esa fecha usan por defecto el vector de su agno.
AGNO_VECTOR = None
INICIO_TITRP = 20140101

MENSAJE_SIN_TASA = (
    "No se entrego tasa de descuento (rv, rp o agno_vector). Desde el 1 de enero de 2014 "
    "rige una tasa unica trimestral de retiro programado (TITRP) publicada por la "
    "Superintendencia de Pensiones, que debe entregarse en rp; el vector de tasas del agno "
    "del siniestro solo se usa por defecto para siniestros anteriores a esa fecha (fsiniestro)."
)

# Roles de la persona cuya mortalidad se modela; coinciden con el tipo de
# tabla historico (rv afiliado, b beneficiario, mi invalido).
ROL_AFILIADO = "rv"
ROL_BENEFICIARIO = "b"
ROL_INVALIDO = "mi"


def agno_actual_por_defecto() -> int:
    return _dt.date.today().year


def _agno(agno_actual: int | None) -> int:
    return agno_actual_por_defecto() if agno_actual is None else int(agno_actual)


def _agno_vector_explicito(agno_vector) -> bool:
    return agno_vector is not None and not _es_missing(agno_vector)


def agno_vector_efectivo(agno_vector: int | None = AGNO_VECTOR, fsiniestro: int = 0) -> int:
    """Agno del vector de tasas que rige cuando no hay tasa constante.

    * ``agno_vector`` explicito -> ese agno;
    * sin ``agno_vector`` y ``fsiniestro`` anterior a :data:`INICIO_TITRP`
      (1 de enero de 2014) -> el agno del siniestro;
    * en cualquier otro caso -> ``ValueError``: desde 2014 rige la TITRP y la
      tasa debe entregarse en ``rp``.
    """
    if _agno_vector_explicito(agno_vector):
        return int(agno_vector)
    fsiniestro = 0 if fsiniestro is None or _es_missing(fsiniestro) else int(fsiniestro)
    if 0 < fsiniestro < INICIO_TITRP:
        return fsiniestro // 10000
    raise ValueError(MENSAJE_SIN_TASA)


def tasas_por_periodo(
    agno_vector: int | None = AGNO_VECTOR,
    rv: float | None = None,
    rp: float | None = None,
    dir_vectores=None,
    fsiniestro: int = 0,
    estricto: bool = True,
) -> np.ndarray | None:
    """Punto unico de resolucion de la tasa de descuento.

    Devuelve el vector de tasas por periodo (``tasas[t-1]`` para el periodo
    ``t``) que usan las funciones escalares, vectoriales, el FAJ, las
    proyecciones y la CLI, con la regla:

    * ``rv`` dado (no ``nan``) -> tasa constante ``rv`` (Renta Vitalicia);
    * ``rp`` dado (no ``nan``) -> tasa constante ``rp`` (Retiro Programado,
      la TITRP);
    * ``agno_vector`` dado -> vector de tasas de ese agno (error si no existe);
    * ninguno y ``fsiniestro`` anterior a :data:`INICIO_TITRP` -> vector del
      agno del siniestro (error que nombra el agno si no esta incluido ni en
      ``dir_vectores``);
    * ninguno en cualquier otro caso -> ``ValueError`` que explica que desde
      enero de 2014 rige la TITRP y debe entregarse en ``rp``.

    :param fsiniestro: fecha del siniestro ``YYYYMMDD`` (0 si no se conoce).
    :param estricto: si es ``False`` devuelve ``None`` en vez de lanzar un
        error cuando no es posible resolver las tasas (sin tasa o vector
        inexistente).
    """
    if rv is not None and not _es_missing(rv):
        return np.full(N_PERIODOS_VECTOR, float(rv))
    if rp is not None and not _es_missing(rp):
        return np.full(N_PERIODOS_VECTOR, float(rp))
    if not estricto:
        try:
            agno = agno_vector_efectivo(agno_vector, fsiniestro)
        except ValueError:
            return None
        return cargar_vector_tasas(agno, dir_vectores) if existe_vector_tasas(agno, dir_vectores) else None
    agno = agno_vector_efectivo(agno_vector, fsiniestro)
    if _agno_vector_explicito(agno_vector):
        return cargar_vector_tasas(agno, dir_vectores)
    try:
        return cargar_vector_tasas(agno, dir_vectores)
    except FileNotFoundError as e:
        raise FileNotFoundError(
            f"El vector de tasas del agno {agno} (cnu_vec{agno}), que corresponde al siniestro "
            f"{int(fsiniestro)}, no esta incluido en el paquete ni en dir_vectores; entregue rp, "
            "agno_vector o dir_vectores"
        ) from e


def edad_entera(edad) -> int:
    """Punto unico de conversion de una edad a entero: edad actuarial.

    Redondea al entero mas cercano con el medio hacia arriba, como exige el
    Compendio de Normas (una fraccion de seis meses o mas cuenta como el agno
    siguiente): ``65.4 -> 65``, ``65.5 -> 66``, ``65.7 -> 66``. Se aplica en
    todas las funciones (escalares, vectoriales, FAJ y proyecciones) antes de
    validar el rango de edades. Ver :func:`edad_actuarial` para obtenerla a
    partir de fechas.
    """
    return math.floor(float(edad) + 0.5)


def _a_fecha(fecha) -> _dt.date:
    """``YYYYMMDD`` (entero) o ``datetime.date`` -> ``datetime.date``."""
    if isinstance(fecha, _dt.datetime):
        return fecha.date()
    if isinstance(fecha, _dt.date):
        return fecha
    fecha = int(fecha)
    return _dt.date(fecha // 10000, fecha // 100 % 100, fecha % 100)


def _mismo_dia(agno: int, mes: int, dia: int) -> _dt.date:
    """Fecha ``agno-mes-dia`` o, si ese dia no existe (29 de febrero), el ultimo del mes."""
    while True:
        try:
            return _dt.date(agno, mes, dia)
        except ValueError:
            dia -= 1


def edad_actuarial(fecha_nacimiento, fecha_calculo) -> int:
    """Edad actuarial a ``fecha_calculo``: la edad exacta redondeada al entero
    mas cercano, con el medio hacia arriba.

    La edad exacta son los agnos cumplidos mas la fraccion transcurrida desde
    el ultimo cumpleagnos, medida en meses y dias (los dias como fraccion del
    mes en curso). Asi, exactamente seis meses despues del cumpleagnos la
    edad se redondea al agno siguiente, y un dia antes de esos seis meses se
    mantiene:

    >>> edad_actuarial(19600915, 20260315)
    66
    >>> edad_actuarial(19600916, 20260315)
    65

    Ambas fechas aceptan enteros ``YYYYMMDD`` (como ``fsiniestro``) u objetos
    ``datetime.date``.
    """
    nac, calc = _a_fecha(fecha_nacimiento), _a_fecha(fecha_calculo)
    if calc < nac:
        raise ValueError("fecha_calculo es anterior a fecha_nacimiento")
    # Meses completos: el "mesiversario" del mes de calculo, si aun no llega, no cuenta.
    meses = (calc.year - nac.year) * 12 + (calc.month - nac.month)
    if calc < _mismo_dia(calc.year, calc.month, nac.day):
        meses -= 1

    def mesiversario(k: int) -> _dt.date:
        agno, mes = divmod(nac.year * 12 + nac.month - 1 + k, 12)
        return _mismo_dia(agno, mes + 1, nac.day)

    ultimo, siguiente = mesiversario(meses), mesiversario(meses + 1)
    fraccion_mes = (calc - ultimo).days / (siguiente - ultimo).days
    return edad_entera((meses + fraccion_mes) / 12)


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


def anualidad(
    qx: np.ndarray,
    edad: int,
    tasas: np.ndarray,
    periodos: int,
    porcentaje: float = 1.0,
    ajuste: float = AJUSTE_MENSUAL,
    qx_afiliado: np.ndarray | None = None,
    x: int | None = None,
    pasos: bool = False,
    encabezado: str = "",
    temporal: bool = False,
) -> float:
    """Nucleo comun de las anualidades del Anexo N 7.

    Con la nomenclatura del Anexo (``x`` edad del afiliado, ``y`` la del
    conyuge, ``h`` la del hijo, ``z = 24`` edad limite de los hijos, ``l_t``
    supervivientes de la tabla al periodo ``t`` e ``i_t`` tasa del periodo
    ``t``), para una persona de ``edad`` con probabilidades de muerte ``qx``
    (ya mejoradas, indexadas por edad) calcula::

        porcentaje * ( sum_{t=0}^{periodos} l_t / (1 + i_t)^t * c_t  -  ajuste )

    donde ``l_0 = 1``, ``l_t = l_{t-1} * (1 - qx[edad + t - 1])`` y ``c_t``
    es la condicion sobre el afiliado:

    * sin ``qx_afiliado``: ``c_t = 1``, anualidad que depende solo de la
      supervivencia de la persona (afiliado, punto 2.1; sobrevivencia,
      punto 1.1); es temporal si ``periodos`` la corta antes de la edad
      maxima (hijos: ``z - h``);
    * con ``qx_afiliado`` y ``x``: ``c_t = 1 - l^x_t``, se paga solo si el
      afiliado de edad ``x`` ha fallecido en el periodo (conyuge de afiliado
      vivo, punto 2.2). Como ``c_0 = 0``, el termino inicial desaparece.

    :param periodos: numero de periodos ``t = 1..periodos`` que se suman
        (limite de periodos): hasta la edad maxima de la tabla
        (``EDAD_MAXIMA - edad``, con la convencion de cada rutina Mata) o
        hasta la edad limite de los hijos (``z - h``).
    :param porcentaje: fraccion del articulo 58 que se aplica al resultado
        (:data:`FRACCION_CONYUGE`, :data:`FRACCION_HIJO`, ...).
    :param ajuste: descuento por pago mensual (:data:`AJUSTE_MENSUAL`); el
        Anexo lo aplica a las anualidades vitalicias no condicionadas y no a
        las vitalicias condicionadas al fallecimiento del afiliado (se pasa
        ``0``).
    :param temporal: anualidad temporal (hijos): el ajuste se aplica con la
        correccion del Anexo para ``N = periodos + 1`` periodos (``N = z - h``),
        con ``v_N = 1 / (1 + i_N)^N``::

            no condicionada:  ajuste * (1 - v_N * l_N)
            condicionada:     ajuste * ((1 - v_N * l_N) - (1 - v_N * l_N * l^x_N))
                            = -ajuste * v_N * l_N * (1 - l^x_N)

        es decir, la anualidad condicionada es la diferencia entre la del
        hijo y la conjunta hijo-afiliado, cada una con su propio ajuste.
    :param pasos: imprime ``encabezado`` (la tabla resuelta) y el calculo
        periodo a periodo.
    :return: valor redondeado a seis decimales.
    """
    return _redondear(porcentaje * _anualidad_bruta(qx, edad, tasas, periodos, ajuste, qx_afiliado, x,
                                                    pasos, encabezado, temporal))


def _anualidad_bruta(
    qx: np.ndarray,
    edad: int,
    tasas: np.ndarray,
    periodos: int,
    ajuste: float = AJUSTE_MENSUAL,
    qx_afiliado: np.ndarray | None = None,
    x: int | None = None,
    pasos: bool = False,
    encabezado: str = "",
    temporal: bool = False,
) -> float:
    """Anualidad de :func:`anualidad` sin porcentaje ni redondeo (``sum - ajuste``).

    Permite componer anualidades por tramos (p.ej. 15% de la temporal y 11%
    de la diferida del hijo invalido parcial) redondeando una sola vez.
    """
    condicionada = qx_afiliado is not None
    ultimo = edad + periodos - 1 + (1 if temporal else 0)
    qx = _qx_hasta(qx, ultimo)
    if condicionada:
        qx_afiliado = _qx_hasta(qx_afiliado, x - edad + ultimo)
    # Termino t = 0: l_0 = 1 y, si esta condicionada, c_0 = 1 - l^x_0 = 0.
    cnu = 0.0 if condicionada else 1.0
    lt = 1.0  # l_t de la persona
    lxt = 1.0  # l^x_t del afiliado
    if pasos:
        if encabezado:
            print(encabezado)
        print("t =   0: CNU = 1")
    for t in range(1, periodos + 1):
        i = tasas[t - 1]
        lt *= 1.0 - qx[edad + t - 1]
        termino = lt / (1.0 + i) ** t
        if condicionada:
            lxt *= 1.0 - qx_afiliado[x + t - 1]
            if pasos:
                print(f"t = {t:3d}: cnu = {cnu:9.6f} + ({lt:g}/(1 + {i:g})^{t})*(1 - {lxt:g})")
            termino *= 1.0 - lxt
        elif pasos:
            print(f"t = {t:3d}: cnu = {cnu:9.6f} + {lt:g}/((1 + {i:g})^{t})")
        cnu += termino
    if temporal:
        n = periodos + 1
        i = tasas[n - 1]
        vl = lt * (1.0 - qx[edad + n - 1]) / (1.0 + i) ** n  # v_N * l_N
        if condicionada:
            lxn = lxt * (1.0 - qx_afiliado[x + n - 1])
            if pasos:
                print(f"t = {n:3d}: ajuste = -11/24*({vl:g})*(1 - {lxn:g})")
            ajuste = -ajuste * vl * (1.0 - lxn)
        else:
            if pasos:
                print(f"t = {n:3d}: ajuste = 11/24*(1 - {vl:g})")
            ajuste = ajuste * (1.0 - vl)
    return cnu - ajuste


def cnu_afiliado(
    x: int,
    mujer: bool = False,
    tabla: str = TABLA_AFILIADO,
    agno_vector: int | None = AGNO_VECTOR,
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
    :param agno_vector: agno del vector de tasas (retiro programado); sin
        el, solo los siniestros anteriores a 2014 usan el vector de su agno.
    :param agno_actual: agno de calculo (por defecto, el del sistema); con
        ``"vigente"`` y sin ``fsiniestro`` la tabla es la vigente al 31 de
        diciembre de este agno.
    :param rv: tasa de renta vitalicia; si se entrega, el CNU es de RV.
    :param rp: tasa unica de retiro programado (TITRP); obligatoria desde
        2014 si no se entrega ``rv`` ni ``agno_vector`` (ver
        :func:`tasas_por_periodo`).
    :param fsiniestro: fecha del siniestro ``YYYYMMDD``; si es distinta de 0,
        el agno de la tabla se asigna dinamicamente y, sin tasa, un siniestro
        anterior a 2014 usa el vector de tasas de su agno.
    :param pasos: imprime el calculo periodo a periodo.
    """
    x = edad_entera(x)
    agno_actual = _agno(agno_actual)
    tm = tabla_mortalidad(tabla, ROL_AFILIADO, mujer, fsiniestro, agno_actual, dir_tablas)
    qx = tm.qx_mejorado(agno_actual, x)
    tasas = tasas_por_periodo(agno_vector, rv, rp, dir_vectores, fsiniestro)
    # Anualidad vitalicia del afiliado menos el ajuste por pago mensual.
    return anualidad(qx, x, tasas, EDAD_MAXIMA - x + 1, pasos=pasos, encabezado=f"tabla {_etiqueta_tabla(tm)}")


def cnu_conyuge(
    x: int,
    y: int,
    cot_mujer: bool = False,
    cony_mujer: bool = True,
    tabla: str = TABLA_AFILIADO,
    tabla_benef: str = TABLA_BENEFICIARIO,
    agno_vector: int | None = AGNO_VECTOR,
    agno_actual: int | None = None,
    rv: float | None = None,
    rp: float | None = None,
    fsiniestro: int = 0,
    pasos: bool = False,
    dir_tablas=None,
    dir_vectores=None,
    conviviente: bool = False,
) -> float:
    """CNU para conyuge (o conviviente civil) sin hijos de un afiliado
    (pension de vejez o invalidez; letra b del punto 2 del Anexo N 7).

    Equivale a ``cnu_cnyg_s_hi`` / ``cnu_2_2``. El resultado se suma al de
    :func:`cnu_afiliado` para obtener el CNU total.

    :param x: edad del afiliado.
    :param y: edad del conyuge.
    :param cot_mujer: ``True`` si el afiliado es mujer.
    :param cony_mujer: ``True`` si el conyuge es mujer.
    :param tabla: tabla del afiliado (p.ej. ``"rv2009"``; por defecto ``"vigente"``).
    :param tabla_benef: tabla del beneficiario (p.ej. ``"b2006"``; por defecto ``"vigente"``).
    :param conviviente: ``True`` si el beneficiario es conviviente civil sin
        hijos comunes ni hijos del causante con derecho a pension (letra m del
        punto 2, incorporada por la NCG N 153 de 2015): la formula es la
        misma con ``a`` (edad del conviviente) en lugar de ``y`` y el valor es
        identico; el parametro documenta el rol del beneficiario.

    La tasa (``rv``, ``rp``, ``agno_vector``, ``fsiniestro``) se resuelve
    como en :func:`cnu_afiliado`.
    """
    x, y = edad_entera(x), edad_entera(y)
    agno_actual = _agno(agno_actual)
    tm_cot = tabla_mortalidad(tabla, ROL_AFILIADO, cot_mujer, fsiniestro, agno_actual, dir_tablas)
    tm_cony = tabla_mortalidad(tabla_benef, ROL_BENEFICIARIO, cony_mujer, fsiniestro, agno_actual, dir_tablas)
    qx_cot = tm_cot.qx_mejorado(agno_actual, x)
    qx_cony = tm_cony.qx_mejorado(agno_actual, y)
    tasas = tasas_por_periodo(agno_vector, rv, rp, dir_vectores, fsiniestro)
    # 60% de la anualidad del conyuge condicionada al fallecimiento del
    # afiliado en el periodo; el Anexo no aplica aqui el ajuste 11/24.
    return anualidad(
        qx_cony, y, tasas, EDAD_MAXIMA - y + 1, FRACCION_CONYUGE, 0.0, qx_cot, x,
        pasos=pasos, encabezado=f"tablas {_etiqueta_tabla(tm_cot)} {_etiqueta_tabla(tm_cony)}",
    )


def cnu_sobrevivencia_conyuge(
    y: int,
    mujer: bool = False,
    tabla_benef: str = TABLA_BENEFICIARIO,
    agno_vector: int | None = AGNO_VECTOR,
    agno_actual: int | None = None,
    rv: float | None = None,
    rp: float | None = None,
    fsiniestro: int = 0,
    pasos: bool = False,
    dir_tablas=None,
    dir_vectores=None,
    conviviente: bool = False,
) -> float:
    """CNU de pension de sobrevivencia para conyuge (o conviviente civil) sin
    hijos (letra a del punto 1 del Anexo N 7).

    Equivale a ``cnu_sobr_cnyg_s_hi`` / ``cnu_1_1``.

    :param y: edad del conyuge.
    :param mujer: ``True`` si el conyuge es mujer.
    :param tabla_benef: tabla de mortalidad del beneficiario (p.ej. ``"b2006"``;
        por defecto ``"vigente"``).
    :param conviviente: ``True`` si el beneficiario es conviviente civil sin
        hijos comunes ni hijos del causante con derecho a pension (letra l del
        punto 1): misma formula con ``a`` en lugar de ``y`` y valor identico.

    La tasa (``rv``, ``rp``, ``agno_vector``, ``fsiniestro``) se resuelve
    como en :func:`cnu_afiliado`.
    """
    y = edad_entera(y)
    agno_actual = _agno(agno_actual)
    tm = tabla_mortalidad(tabla_benef, ROL_BENEFICIARIO, mujer, fsiniestro, agno_actual, dir_tablas)
    qx = tm.qx_mejorado(agno_actual, y)
    tasas = tasas_por_periodo(agno_vector, rv, rp, dir_vectores, fsiniestro)
    # 60% de la anualidad vitalicia del conyuge menos el ajuste por pago mensual.
    return anualidad(qx, y, tasas, EDAD_MAXIMA - y, FRACCION_CONYUGE, pasos=pasos,
                     encabezado=f"tabla {_etiqueta_tabla(tm)}")


def cnu_hijo(
    x: int,
    h: int,
    cot_mujer: bool = False,
    hijo_mujer: bool = False,
    tabla: str = TABLA_AFILIADO,
    tabla_benef: str = TABLA_BENEFICIARIO,
    agno_vector: int | None = AGNO_VECTOR,
    agno_actual: int | None = None,
    rv: float | None = None,
    rp: float | None = None,
    fsiniestro: int = 0,
    pasos: bool = False,
    dir_tablas=None,
    dir_vectores=None,
) -> float:
    """CNU de un hijo no invalido de un afiliado pensionado por vejez o
    invalidez (letra e del punto 2 del Anexo N 7: hijos no invalidos y
    causante con conyuge, o hijos no invalidos con madre o padre con derecho
    a pension). Sin rutina Mata equivalente.

    Con ``z = 24`` (:data:`EDAD_LIMITE_HIJO`), ``l`` los supervivientes de
    cada tabla e ``i_t`` la tasa del periodo ``t``, el Anexo define::

        cnu = 0,15 * [ sum_{t=0}^{23-h} l_{h+t} / (l_h (1+i_t)^t)
                       - sum_{t=0}^{23-h} l_{h+t} l_{x+t} / (l_h l_x (1+i_t)^t)
                       - 11/24 * 1/(1+i_{24-h})^{24-h}
                         * ( l_{x+24-h} l_24 / (l_x l_h) - l_24 / l_h ) ]

    Es la anualidad temporal del hijo hasta la edad limite, pagadera solo
    si el afiliado ha fallecido (``1 - l^x_t``), con el ajuste por pago
    mensual de una anualidad temporal, al 15% del articulo 58 del D.L.
    N 3.500 (:data:`FRACCION_HIJO`). Con ``h >= 24`` no hay periodos y el
    CNU es 0. El resultado se suma al de :func:`cnu_afiliado` (y al del
    conyuge, si lo hay) para obtener el CNU total.

    No cubre la letra g del punto 2 (hijos sin conyuge ni madre o padre con
    derecho a pension), cuyo porcentaje es ``0,15 + 0,5/n``.

    :param x: edad del afiliado.
    :param h: edad del hijo (desde 0 agnos).
    :param cot_mujer: ``True`` si el afiliado es mujer.
    :param hijo_mujer: ``True`` si el hijo es mujer.
    :param tabla: tabla del afiliado (p.ej. ``"rv2009"``; por defecto ``"vigente"``).
    :param tabla_benef: tabla del hijo, con rol de beneficiario (p.ej.
        ``"b2006"``; por defecto ``"vigente"``).

    La tasa (``rv``, ``rp``, ``agno_vector``, ``fsiniestro``) se resuelve
    como en :func:`cnu_afiliado`.
    """
    x, h = edad_entera(x), edad_entera(h)
    agno_actual = _agno(agno_actual)
    tm_cot = tabla_mortalidad(tabla, ROL_AFILIADO, cot_mujer, fsiniestro, agno_actual, dir_tablas)
    tm_hijo = tabla_mortalidad(tabla_benef, ROL_BENEFICIARIO, hijo_mujer, fsiniestro, agno_actual, dir_tablas)
    tasas = tasas_por_periodo(agno_vector, rv, rp, dir_vectores, fsiniestro)
    encabezado = f"tablas {_etiqueta_tabla(tm_cot)} {_etiqueta_tabla(tm_hijo)}"
    if h >= EDAD_LIMITE_HIJO:
        if pasos:
            print(encabezado)
            print(f"hijo de {h} agnos: sin derecho desde los {EDAD_LIMITE_HIJO}, CNU = 0")
        return 0.0
    # 15% de la anualidad temporal del hijo (t = 0..23-h) condicionada al
    # fallecimiento del afiliado, con el ajuste 11/24 temporal del Anexo.
    return anualidad(
        tm_hijo.qx_mejorado(agno_actual, h), h, tasas, EDAD_LIMITE_HIJO - 1 - h, FRACCION_HIJO,
        AJUSTE_MENSUAL, tm_cot.qx_mejorado(agno_actual, x), x,
        pasos=pasos, encabezado=encabezado, temporal=True,
    )


def cnu_sobrevivencia_hijo(
    h: int,
    mujer: bool = False,
    tabla_benef: str = TABLA_BENEFICIARIO,
    agno_vector: int | None = AGNO_VECTOR,
    agno_actual: int | None = None,
    rv: float | None = None,
    rp: float | None = None,
    fsiniestro: int = 0,
    pasos: bool = False,
    dir_tablas=None,
    dir_vectores=None,
) -> float:
    """CNU de pension de sobrevivencia para un hijo no invalido (letra d del
    punto 1 del Anexo N 7: hijos no invalidos y causante con conyuge, o
    hijos no invalidos con madre o padre con derecho a pension). Sin rutina
    Mata equivalente.

    Con ``z = 24`` (:data:`EDAD_LIMITE_HIJO`), el Anexo define::

        cnu = 0,15 * [ sum_{t=0}^{23-h} l_{h+t} / (l_h (1+i_t)^t)
                       - 11/24 * ( 1 - l_24 / (l_h (1+i_{24-h})^{24-h}) ) ]

    Es la anualidad temporal del hijo hasta la edad limite, con el ajuste
    por pago mensual de una anualidad temporal, al 15% del articulo 58 del
    D.L. N 3.500 (:data:`FRACCION_HIJO`). Con ``h >= 24`` el CNU es 0.

    No cubre la letra f del punto 1 (hijos sin conyuge ni madre o padre con
    derecho a pension, porcentaje ``0,15 + 0,5/n``) ni la regla del grupo
    familiar compuesto por un solo hijo de 23 o mas agnos (meses que le
    restan para cumplir 24).

    :param h: edad del hijo (desde 0 agnos).
    :param mujer: ``True`` si el hijo es mujer.
    :param tabla_benef: tabla de mortalidad del hijo, con rol de
        beneficiario (p.ej. ``"b2006"``; por defecto ``"vigente"``).

    La tasa (``rv``, ``rp``, ``agno_vector``, ``fsiniestro``) se resuelve
    como en :func:`cnu_afiliado`.
    """
    h = edad_entera(h)
    agno_actual = _agno(agno_actual)
    tm = tabla_mortalidad(tabla_benef, ROL_BENEFICIARIO, mujer, fsiniestro, agno_actual, dir_tablas)
    tasas = tasas_por_periodo(agno_vector, rv, rp, dir_vectores, fsiniestro)
    encabezado = f"tabla {_etiqueta_tabla(tm)}"
    if h >= EDAD_LIMITE_HIJO:
        if pasos:
            print(encabezado)
            print(f"hijo de {h} agnos: sin derecho desde los {EDAD_LIMITE_HIJO}, CNU = 0")
        return 0.0
    # 15% de la anualidad temporal del hijo (t = 0..23-h) menos el ajuste
    # 11/24 temporal del Anexo.
    return anualidad(tm.qx_mejorado(agno_actual, h), h, tasas, EDAD_LIMITE_HIJO - 1 - h, FRACCION_HIJO,
                     pasos=pasos, encabezado=encabezado, temporal=True)


def _tramos_edad_limite(
    vitalicia: float, temporal: float, h: int, pasos: bool, fraccion_temporal: float, fraccion_diferida: float
) -> float:
    """Dos tramos separados por la edad limite del hijo de edad ``h`` (menor de
    24): ``fraccion_temporal`` de la anualidad temporal hasta que cumple 24 y
    ``fraccion_diferida`` de la diferida desde entonces (vitalicia menos
    temporal), cada una con su propio ajuste 11/24, redondeando una sola vez.
    Sirve al hijo invalido parcial (15%/11%) y al conyuge con hijos (50%/60%)."""
    diferida = vitalicia - temporal
    n = EDAD_LIMITE_HIJO - h
    if pasos:
        print(f"tramos: {fraccion_temporal:.0%} * {temporal:.6f} (t = 0..{n - 1}, hasta los {EDAD_LIMITE_HIJO} "
              f"del hijo) + {fraccion_diferida:.0%} * {diferida:.6f} (t >= {n})")
    return _redondear(fraccion_temporal * temporal + fraccion_diferida * diferida)


def _tramos_hijo_invalido_parcial(vitalicia: float, temporal: float, h: int, pasos: bool) -> float:
    """Hijo invalido parcial menor de 24: 15% hasta los 24 y 11% despues."""
    return _tramos_edad_limite(vitalicia, temporal, h, pasos, FRACCION_HIJO, FRACCION_HIJO_INVALIDO_PARCIAL)


def _tramos_con_hijos(
    vitalicia: float, temporal, y: int, h: int | None, hijo_invalido: bool, pasos: bool,
    quien: str, fraccion_con_hijos: float, fraccion_sin_hijos: float,
) -> float:
    """Porcentaje de un beneficiario cuyo tramo depende de los hijos con
    derecho (conyuge 50%/60%, madre o padre no matrimonial 30%/36%) sobre su
    anualidad bruta ``vitalicia``: ``fraccion_con_hijos`` vitalicia con algun
    hijo invalido; ``fraccion_sin_hijos`` vitalicia sin hijos con derecho
    (``h`` es ``None``) o si el hijo menor ya tiene 24; ``fraccion_con_hijos``
    vitalicia si el beneficiario supera la edad maxima antes de que el hijo
    cumpla 24 (el tramo diferido es nulo); en otro caso dos tramos, con
    ``temporal(periodos)`` la anualidad temporal bruta de ese numero de
    periodos."""
    if hijo_invalido:
        if pasos:
            print(f"{quien} con algun hijo invalido con derecho a pension: {fraccion_con_hijos:.0%} vitalicio")
        return _redondear(fraccion_con_hijos * vitalicia)
    if h is None:
        if pasos:
            print(f"{quien} sin hijos con derecho a pension: {fraccion_sin_hijos:.0%} vitalicio")
        return _redondear(fraccion_sin_hijos * vitalicia)
    if h >= EDAD_LIMITE_HIJO:
        if pasos:
            print(f"hijo menor de {h} agnos: sin derecho desde los {EDAD_LIMITE_HIJO}, "
                  f"{fraccion_sin_hijos:.0%} vitalicio como sin hijos")
        return _redondear(fraccion_sin_hijos * vitalicia)
    if y + EDAD_LIMITE_HIJO - h > EDAD_MAXIMA:
        if pasos:
            print(f"{quien} de {y} agnos supera los {EDAD_MAXIMA} antes de que el hijo cumpla {EDAD_LIMITE_HIJO}: "
                  f"{fraccion_con_hijos:.0%} vitalicio")
        return _redondear(fraccion_con_hijos * vitalicia)
    return _tramos_edad_limite(vitalicia, temporal(EDAD_LIMITE_HIJO - 1 - h), h, pasos,
                               fraccion_con_hijos, fraccion_sin_hijos)


def _tramos_conyuge_con_hijos(vitalicia: float, temporal, y: int, h: int, hijo_invalido: bool, pasos: bool) -> float:
    """Conyuge con hijos: 50% mientras el hijo menor tenga derecho y 60% despues."""
    return _tramos_con_hijos(vitalicia, temporal, y, h, hijo_invalido, pasos, "conyuge",
                             FRACCION_CONYUGE_CON_HIJOS, FRACCION_CONYUGE)


def _tramos_madre_padre(vitalicia: float, temporal, u: int, h: int | None, hijo_invalido: bool, pasos: bool) -> float:
    """Madre o padre no matrimonial: 30% mientras haya hijos con derecho y 36% despues (o sin hijos)."""
    return _tramos_con_hijos(vitalicia, temporal, u, h, hijo_invalido, pasos, "madre o padre",
                             FRACCION_MADRE_PADRE_CON_HIJOS, FRACCION_MADRE_PADRE)


def _edad_hijo_opcional(h) -> int | None:
    """Edad del hijo menor con derecho, o ``None`` (tambien ``nan``) si no hay hijos con derecho."""
    return None if h is None or _es_missing(h) else edad_entera(h)


def cnu_hijo_invalido(
    x: int,
    h: int,
    cot_mujer: bool = False,
    hijo_mujer: bool = False,
    parcial: bool = False,
    tabla: str = TABLA_AFILIADO,
    tabla_benef: str = TABLA_BENEFICIARIO,
    agno_vector: int | None = AGNO_VECTOR,
    agno_actual: int | None = None,
    rv: float | None = None,
    rp: float | None = None,
    fsiniestro: int = 0,
    pasos: bool = False,
    dir_tablas=None,
    dir_vectores=None,
) -> float:
    """CNU de un hijo invalido (total o parcial) de un afiliado pensionado
    por vejez o invalidez (letra f del punto 2 del Anexo N 7: hijos
    invalidos y causante con conyuge, o hijos invalidos con madre o padre con
    derecho a pension). Sin rutina Mata equivalente.

    Con ``hi`` la edad del hijo, ``z = 24`` (:data:`EDAD_LIMITE_HIJO`), ``l``
    los supervivientes de cada tabla (la del hijo es la de invalidos, ``mi``)
    e ``i_t`` la tasa del periodo ``t``, el Anexo define para el hijo
    invalido total::

        cnu = 0,15 * sum_{t=0}^{w} l_{hi+t} (1 - l_{x+t} / l_x) / (l_hi (1+i_t)^t)

    y para el hijo invalido parcial con ``hi < 24``::

        cnu = 0,15 * sum_{t=0}^{23-hi} l_{hi+t} (1 - l_{x+t} / l_x) / (l_hi (1+i_t)^t)
              + 0,11 * sum_{t=0}^{w} l_{24+t} (1 - l_{x+24-hi+t} / l_x)
                       / (l_hi (1+i_{24-hi+t})^{24-hi+t})
              + 0,04 * 11/24 * l_24 (1 - l_{x+24-hi} / l_x) / (l_hi (1+i_{24-hi})^{24-hi})

    y con ``hi >= 24`` la misma anualidad vitalicia del caso total al 11%.
    Es la anualidad vitalicia del hijo condicionada al fallecimiento del
    afiliado (``1 - l^x_t``), sin ajuste por pago mensual, al 15% del
    articulo 58 del D.L. N 3.500 (:data:`FRACCION_HIJO`); en el caso parcial
    se paga 15% mientras el hijo es menor de 24 y 11%
    (:data:`FRACCION_HIJO_INVALIDO_PARCIAL`) desde entonces, es decir, 15%
    de la anualidad temporal hasta los 24 (con su ajuste, como en
    :func:`cnu_hijo`) mas 11% de la anualidad diferida (vitalicia menos
    temporal). No hay edad limite: un hijo invalido de 30 o mas agnos tiene
    CNU positivo. El resultado se suma al de :func:`cnu_afiliado` (y al del
    conyuge, si lo hay) para obtener el CNU total.

    No cubre la letra h del punto 2 (hijos invalidos sin conyuge ni madre o
    padre con derecho a pension), cuyo porcentaje incluye ``0,5/n``.

    :param x: edad del afiliado.
    :param h: edad del hijo invalido (desde 0 agnos, sin edad limite).
    :param cot_mujer: ``True`` si el afiliado es mujer.
    :param hijo_mujer: ``True`` si el hijo es mujer.
    :param parcial: ``True`` si la invalidez es parcial (15% hasta los 24 y
        11% despues); ``False`` (por defecto) si es total (15% vitalicio).
    :param tabla: tabla del afiliado (p.ej. ``"rv2009"``; por defecto ``"vigente"``).
    :param tabla_benef: tabla del hijo, con rol de invalido (p.ej.
        ``"mi2006"``; por defecto ``"vigente"``, la ``mi`` vigente a la fecha).

    La tasa (``rv``, ``rp``, ``agno_vector``, ``fsiniestro``) se resuelve
    como en :func:`cnu_afiliado`.
    """
    x, h = edad_entera(x), edad_entera(h)
    agno_actual = _agno(agno_actual)
    tm_cot = tabla_mortalidad(tabla, ROL_AFILIADO, cot_mujer, fsiniestro, agno_actual, dir_tablas)
    tm_hijo = tabla_mortalidad(tabla_benef, ROL_INVALIDO, hijo_mujer, fsiniestro, agno_actual, dir_tablas)
    tasas = tasas_por_periodo(agno_vector, rv, rp, dir_vectores, fsiniestro)
    qx_hijo, qx_cot = tm_hijo.qx_mejorado(agno_actual, h), tm_cot.qx_mejorado(agno_actual, x)
    encabezado = f"tablas {_etiqueta_tabla(tm_cot)} {_etiqueta_tabla(tm_hijo)}"
    # Anualidad vitalicia del hijo condicionada al fallecimiento del afiliado
    # en el periodo; el Anexo no aplica aqui el ajuste 11/24.
    vitalicia = _anualidad_bruta(qx_hijo, h, tasas, EDAD_MAXIMA - h + 1, 0.0, qx_cot, x, pasos, encabezado)
    if not parcial:
        return _redondear(FRACCION_HIJO * vitalicia)
    if h >= EDAD_LIMITE_HIJO:
        if pasos:
            print(f"hijo invalido parcial de {h} agnos: 11% vitalicio desde los {EDAD_LIMITE_HIJO}")
        return _redondear(FRACCION_HIJO_INVALIDO_PARCIAL * vitalicia)
    temporal = _anualidad_bruta(qx_hijo, h, tasas, EDAD_LIMITE_HIJO - 1 - h, AJUSTE_MENSUAL, qx_cot, x,
                                temporal=True)
    return _tramos_hijo_invalido_parcial(vitalicia, temporal, h, pasos)


def cnu_sobrevivencia_hijo_invalido(
    h: int,
    mujer: bool = False,
    parcial: bool = False,
    tabla_benef: str = TABLA_BENEFICIARIO,
    agno_vector: int | None = AGNO_VECTOR,
    agno_actual: int | None = None,
    rv: float | None = None,
    rp: float | None = None,
    fsiniestro: int = 0,
    pasos: bool = False,
    dir_tablas=None,
    dir_vectores=None,
) -> float:
    """CNU de pension de sobrevivencia para un hijo invalido, total o parcial
    (letra e del punto 1 del Anexo N 7: hijos invalidos y causante con
    conyuge, o hijos invalidos con madre o padre con derecho a pension). Sin
    rutina Mata equivalente.

    Con ``hi`` la edad del hijo, ``z = 24`` (:data:`EDAD_LIMITE_HIJO`) y ``l``
    los supervivientes de la tabla de invalidos (``mi``) de su sexo, el Anexo
    define para el hijo invalido total::

        cnu = 0,15 * [ sum_{t=0}^{w} l_{hi+t} / (l_hi (1+i_t)^t) - 11/24 ]

    y para el hijo invalido parcial con ``hi < 24``::

        cnu = 0,15 * [ sum_{t=0}^{23-hi} l_{hi+t} / (l_hi (1+i_t)^t)
                       - 11/24 * (1 - l_24 / (l_hi (1+i_{24-hi})^{24-hi})) ]
              + 0,11 * [ sum_{t=0}^{w} l_{24+t} / (l_hi (1+i_{24-hi+t})^{24-hi+t})
                         - 11/24 * l_24 / (l_hi (1+i_{24-hi})^{24-hi}) ]

    y con ``hi >= 24`` la misma anualidad vitalicia del caso total al 11%.
    Es la anualidad vitalicia del hijo menos el ajuste por pago mensual, al
    15% del articulo 58 del D.L. N 3.500 (:data:`FRACCION_HIJO`); en el
    caso parcial, 15% de la anualidad temporal hasta los 24 (con el ajuste
    temporal de :func:`cnu_sobrevivencia_hijo`) mas 11%
    (:data:`FRACCION_HIJO_INVALIDO_PARCIAL`) de la anualidad diferida
    (vitalicia menos temporal). No hay edad limite.

    No cubre la letra g del punto 1 (hijos invalidos sin conyuge ni madre o
    padre con derecho a pension), cuyo porcentaje incluye ``0,5/n``.

    :param h: edad del hijo invalido (desde 0 agnos, sin edad limite).
    :param mujer: ``True`` si el hijo es mujer.
    :param parcial: ``True`` si la invalidez es parcial (15% hasta los 24 y
        11% despues); ``False`` (por defecto) si es total (15% vitalicio).
    :param tabla_benef: tabla de mortalidad del hijo, con rol de invalido
        (p.ej. ``"mi2006"``; por defecto ``"vigente"``, la ``mi`` vigente).

    La tasa (``rv``, ``rp``, ``agno_vector``, ``fsiniestro``) se resuelve
    como en :func:`cnu_afiliado`.
    """
    h = edad_entera(h)
    agno_actual = _agno(agno_actual)
    tm = tabla_mortalidad(tabla_benef, ROL_INVALIDO, mujer, fsiniestro, agno_actual, dir_tablas)
    tasas = tasas_por_periodo(agno_vector, rv, rp, dir_vectores, fsiniestro)
    qx = tm.qx_mejorado(agno_actual, h)
    # Anualidad vitalicia del hijo menos el ajuste por pago mensual.
    vitalicia = _anualidad_bruta(qx, h, tasas, EDAD_MAXIMA - h, AJUSTE_MENSUAL, pasos=pasos,
                                 encabezado=f"tabla {_etiqueta_tabla(tm)}")
    if not parcial:
        return _redondear(FRACCION_HIJO * vitalicia)
    if h >= EDAD_LIMITE_HIJO:
        if pasos:
            print(f"hijo invalido parcial de {h} agnos: 11% vitalicio desde los {EDAD_LIMITE_HIJO}")
        return _redondear(FRACCION_HIJO_INVALIDO_PARCIAL * vitalicia)
    temporal = _anualidad_bruta(qx, h, tasas, EDAD_LIMITE_HIJO - 1 - h, AJUSTE_MENSUAL, temporal=True)
    return _tramos_hijo_invalido_parcial(vitalicia, temporal, h, pasos)


def cnu_conyuge_con_hijos(
    x: int,
    y: int,
    h: int,
    cot_mujer: bool = False,
    cony_mujer: bool = True,
    hijo_invalido: bool = False,
    tabla: str = TABLA_AFILIADO,
    tabla_benef: str = TABLA_BENEFICIARIO,
    agno_vector: int | None = AGNO_VECTOR,
    agno_actual: int | None = None,
    rv: float | None = None,
    rp: float | None = None,
    fsiniestro: int = 0,
    pasos: bool = False,
    dir_tablas=None,
    dir_vectores=None,
    conviviente: bool = False,
) -> float:
    """CNU del conyuge (o conviviente civil) con hijos con derecho a pension
    de un afiliado pensionado por vejez o invalidez (letras c y d del punto 2
    del Anexo N 7). Sin rutina Mata equivalente.

    Con ``h`` la edad del hijo menor no invalido con derecho, ``z = 24``
    (:data:`EDAD_LIMITE_HIJO`), ``y' = y + z - h`` y ``x' = x + z - h`` (edades
    del conyuge y del afiliado cuando ese hijo cumple 24), ``l`` los
    supervivientes de cada tabla e ``i_t`` la tasa del periodo ``t``, la letra
    c (modificada por la NCG N 260 de 2020) define::

        cnu = 0,5 * sum_{t=0}^{w} l_{y+t} (1 - l_{x+t}/l_x) / (l_y (1+i_t)^t)
              + 0,1 * sum_{t=0}^{w} l_{y'+t} (1 - l_{x'+t}/l_x) / (l_y (1+i_{y'-y+t})^{y'-y+t})
              - 0,1 * 11/24 * l_{y'} (1 - l_{x'}/l_x) / (l_y (1+i_{y'-y})^{y'-y})

    Es la anualidad del conyuge condicionada al fallecimiento del afiliado
    (``1 - l^x_t``, como en :func:`cnu_conyuge`) en dos tramos del articulo 58
    del D.L. N 3.500: 50% (:data:`FRACCION_CONYUGE_CON_HIJOS`) mientras el
    hijo menor tiene derecho, es decir, de la anualidad temporal hasta ``y'``
    (con el ajuste temporal 11/24 de :func:`cnu_hijo`), y 60%
    (:data:`FRACCION_CONYUGE`) de la anualidad diferida desde entonces
    (vitalicia menos temporal): ``0,5 * temporal + 0,6 * (vitalicia -
    temporal)``, que reordenado es la formula del Anexo. Con ``h >= 24`` no
    hay tramo al 50% y el resultado coincide con :func:`cnu_conyuge`; si el
    conyuge supera los 110 agnos antes de ``y'`` el tramo al 60% es nulo y
    queda el 50% vitalicio.

    Con ``hijo_invalido`` (letra d: conyuge con algun hijo invalido con derecho
    a pension) el hijo no pierde el derecho y el conyuge queda al 50%
    vitalicio; ``h`` no interviene::

        cnu = 0,5 * sum_{t=0}^{w} l_{y+t} (1 - l_{x+t}/l_x) / (l_y (1+i_t)^t)

    El resultado se suma al de :func:`cnu_afiliado` y al de cada hijo
    (:func:`cnu_hijo`, :func:`cnu_hijo_invalido`) para obtener el CNU total.
    No cubre al conviviente civil sin hijos comunes que concurre con hijos del
    causante (letras n y p del punto 2, 15% mientras haya hijos con derecho).

    :param x: edad del afiliado.
    :param y: edad del conyuge.
    :param h: edad del hijo menor con derecho a pension (desde 0 agnos); con
        24 o mas el resultado es el de :func:`cnu_conyuge`. Se ignora con
        ``hijo_invalido``.
    :param cot_mujer: ``True`` si el afiliado es mujer.
    :param cony_mujer: ``True`` si el conyuge es mujer.
    :param hijo_invalido: ``True`` si algun hijo con derecho es invalido (50%
        vitalicio, letra d).
    :param tabla: tabla del afiliado (p.ej. ``"rv2009"``; por defecto ``"vigente"``).
    :param tabla_benef: tabla del conyuge, con rol de beneficiario (p.ej.
        ``"b2006"``; por defecto ``"vigente"``).
    :param conviviente: ``True`` si el beneficiario es conviviente civil con
        hijos comunes con el causante (letras o y q del punto 2, NCG N 153 de
        2015): misma formula con ``a`` en lugar de ``y`` y valor identico.

    La tasa (``rv``, ``rp``, ``agno_vector``, ``fsiniestro``) se resuelve
    como en :func:`cnu_afiliado`.
    """
    x, y, h = edad_entera(x), edad_entera(y), edad_entera(h)
    agno_actual = _agno(agno_actual)
    tm_cot = tabla_mortalidad(tabla, ROL_AFILIADO, cot_mujer, fsiniestro, agno_actual, dir_tablas)
    tm_cony = tabla_mortalidad(tabla_benef, ROL_BENEFICIARIO, cony_mujer, fsiniestro, agno_actual, dir_tablas)
    qx_cot, qx_cony = tm_cot.qx_mejorado(agno_actual, x), tm_cony.qx_mejorado(agno_actual, y)
    tasas = tasas_por_periodo(agno_vector, rv, rp, dir_vectores, fsiniestro)
    encabezado = f"tablas {_etiqueta_tabla(tm_cot)} {_etiqueta_tabla(tm_cony)}"
    # Anualidad vitalicia del conyuge condicionada al fallecimiento del
    # afiliado en el periodo (sin ajuste 11/24), la misma de cnu_conyuge.
    vitalicia = _anualidad_bruta(qx_cony, y, tasas, EDAD_MAXIMA - y + 1, 0.0, qx_cot, x, pasos, encabezado)

    def temporal(periodos: int) -> float:
        return _anualidad_bruta(qx_cony, y, tasas, periodos, AJUSTE_MENSUAL, qx_cot, x, temporal=True)

    return _tramos_conyuge_con_hijos(vitalicia, temporal, y, h, hijo_invalido, pasos)


def cnu_sobrevivencia_conyuge_con_hijos(
    y: int,
    h: int,
    mujer: bool = False,
    hijo_invalido: bool = False,
    tabla_benef: str = TABLA_BENEFICIARIO,
    agno_vector: int | None = AGNO_VECTOR,
    agno_actual: int | None = None,
    rv: float | None = None,
    rp: float | None = None,
    fsiniestro: int = 0,
    pasos: bool = False,
    dir_tablas=None,
    dir_vectores=None,
    conviviente: bool = False,
) -> float:
    """CNU de pension de sobrevivencia para conyuge (o conviviente civil) con
    hijos con derecho a pension (letras b y c del punto 1 del Anexo N 7). Sin
    rutina Mata equivalente.

    Con ``h`` la edad del hijo menor no invalido con derecho, ``z = 24``
    (:data:`EDAD_LIMITE_HIJO`) e ``y' = y + z - h``, la letra b define::

        cnu = 0,5 * [ sum_{t=0}^{w} l_{y+t} / (l_y (1+i_t)^t) - 11/24 ]
              + 0,1 * [ sum_{t=0}^{w} l_{y'+t} / (l_y (1+i_{y'-y+t})^{y'-y+t})
                        - 11/24 * l_{y'} / (l_y (1+i_{y'-y})^{y'-y}) ]

    Es la anualidad vitalicia del conyuge en dos tramos del articulo 58 del
    D.L. N 3.500: 50% (:data:`FRACCION_CONYUGE_CON_HIJOS`) de la anualidad
    temporal hasta ``y'`` (con el ajuste temporal de
    :func:`cnu_sobrevivencia_hijo`) y 60% (:data:`FRACCION_CONYUGE`) de la
    diferida desde entonces (vitalicia menos temporal): ``0,5 * temporal +
    0,6 * (vitalicia - temporal)``, que reordenado es la formula del Anexo.
    Con ``h >= 24`` coincide con :func:`cnu_sobrevivencia_conyuge`; si el
    conyuge supera los 110 agnos antes de ``y'`` queda el 50% vitalicio.

    Con ``hijo_invalido`` (letra c: conyuge con algun hijo invalido con
    derecho a pension) el conyuge queda al 50% vitalicio y ``h`` no
    interviene::

        cnu = 0,5 * [ sum_{t=0}^{w} l_{y+t} / (l_y (1+i_t)^t) - 11/24 ]

    No cubre al conviviente civil sin hijos comunes que concurre con hijos del
    causante (letras m y o del punto 1, 15% mientras haya hijos con derecho).

    :param y: edad del conyuge.
    :param h: edad del hijo menor con derecho a pension (desde 0 agnos); se
        ignora con ``hijo_invalido``.
    :param mujer: ``True`` si el conyuge es mujer.
    :param hijo_invalido: ``True`` si algun hijo con derecho es invalido (50%
        vitalicio, letra c).
    :param tabla_benef: tabla de mortalidad del conyuge, con rol de
        beneficiario (p.ej. ``"b2006"``; por defecto ``"vigente"``).
    :param conviviente: ``True`` si el beneficiario es conviviente civil con
        hijos comunes con el causante (letras n y p del punto 1): misma
        formula con ``a`` en lugar de ``y`` y valor identico.

    La tasa (``rv``, ``rp``, ``agno_vector``, ``fsiniestro``) se resuelve
    como en :func:`cnu_afiliado`.
    """
    y, h = edad_entera(y), edad_entera(h)
    agno_actual = _agno(agno_actual)
    tm = tabla_mortalidad(tabla_benef, ROL_BENEFICIARIO, mujer, fsiniestro, agno_actual, dir_tablas)
    qx = tm.qx_mejorado(agno_actual, y)
    tasas = tasas_por_periodo(agno_vector, rv, rp, dir_vectores, fsiniestro)
    # Anualidad vitalicia del conyuge menos el ajuste por pago mensual, la
    # misma de cnu_sobrevivencia_conyuge.
    vitalicia = _anualidad_bruta(qx, y, tasas, EDAD_MAXIMA - y, AJUSTE_MENSUAL, pasos=pasos,
                                 encabezado=f"tabla {_etiqueta_tabla(tm)}")

    def temporal(periodos: int) -> float:
        return _anualidad_bruta(qx, y, tasas, periodos, AJUSTE_MENSUAL, temporal=True)

    return _tramos_conyuge_con_hijos(vitalicia, temporal, y, h, hijo_invalido, pasos)


def cnu_madre_padre(
    x: int,
    u: int,
    h: int | None = None,
    cot_mujer: bool = False,
    madre: bool = True,
    hijo_invalido: bool = False,
    tabla: str = TABLA_AFILIADO,
    tabla_benef: str = TABLA_BENEFICIARIO,
    agno_vector: int | None = AGNO_VECTOR,
    agno_actual: int | None = None,
    rv: float | None = None,
    rp: float | None = None,
    fsiniestro: int = 0,
    pasos: bool = False,
    dir_tablas=None,
    dir_vectores=None,
) -> float:
    """CNU de la madre o el padre de hijos de filiacion no matrimonial de un
    afiliado pensionado por vejez o invalidez (letras i, j y k del punto 2 del
    Anexo N 7). Sin rutina Mata equivalente.

    Con ``u`` la edad de la madre o el padre, ``h`` la del hijo menor no
    invalido con derecho, ``z = 24`` (:data:`EDAD_LIMITE_HIJO`), ``u' = u + z
    - h`` y ``x' = x + z - h``, ``l`` los supervivientes de cada tabla e
    ``i_t`` la tasa del periodo ``t``, el Anexo define, con la misma
    estructura que el conyuge (:func:`cnu_conyuge_con_hijos`) y los
    porcentajes del articulo 58 del D.L. N 3.500:

    * letra i, sin hijos con derecho a pension (``h`` es ``None``), 36%
      (:data:`FRACCION_MADRE_PADRE`) vitalicio::

          cnu = 0,36 * sum_{t=0}^{w} l_{u+t} (1 - l_{x+t}/l_x) / (l_u (1+i_t)^t)

    * letra j, con hijos no invalidos con derecho, 30%
      (:data:`FRACCION_MADRE_PADRE_CON_HIJOS`) mientras el hijo menor tenga
      derecho y 36% despues::

          cnu = 0,30 * sum_{t=0}^{w} l_{u+t} (1 - l_{x+t}/l_x) / (l_u (1+i_t)^t)
                + 0,06 * sum_{t=0}^{w} l_{u'+t} (1 - l_{x'+t}/l_x) / (l_u (1+i_{u'-u+t})^{u'-u+t})
                - 0,06 * 11/24 * l_{u'} (1 - l_{x'}/l_x) / (l_u (1+i_{u'-u})^{u'-u})

      es decir, ``0,30 * temporal + 0,36 * (vitalicia - temporal)`` con la
      anualidad temporal hasta ``u'`` (ajuste temporal 11/24 de
      :func:`cnu_hijo`). Con ``h >= 24`` coincide con la letra i; si la madre
      o el padre supera los 110 agnos antes de ``u'`` queda el 30% vitalicio;

    * letra k, con algun hijo invalido con derecho (``hijo_invalido``), 30%
      vitalicio y ``h`` no interviene::

          cnu = 0,30 * sum_{t=0}^{w} l_{u+t} (1 - l_{x+t}/l_x) / (l_u (1+i_t)^t)

    Es la anualidad de la madre o el padre condicionada al fallecimiento del
    afiliado (``1 - l^x_t``), sin ajuste 11/24 en el tramo vitalicio, como en
    :func:`cnu_conyuge`. El resultado se suma al de :func:`cnu_afiliado` y al
    de cada hijo para obtener el CNU total.

    :param x: edad del afiliado.
    :param u: edad de la madre o el padre de los hijos no matrimoniales.
    :param h: edad del hijo menor con derecho a pension (desde 0 agnos), o
        ``None`` (por defecto) si no hay hijos con derecho; con 24 o mas
        equivale a ``None``. Se ignora con ``hijo_invalido``.
    :param cot_mujer: ``True`` si el afiliado es mujer.
    :param madre: ``True`` (por defecto) si la beneficiaria es la madre;
        ``False`` si es el padre. Fija el sexo de la tabla de beneficiario.
    :param hijo_invalido: ``True`` si algun hijo con derecho es invalido (30%
        vitalicio, letra k).
    :param tabla: tabla del afiliado (p.ej. ``"rv2009"``; por defecto ``"vigente"``).
    :param tabla_benef: tabla de la madre o el padre, con rol de beneficiario
        (p.ej. ``"b2006"``; por defecto ``"vigente"``).

    La tasa (``rv``, ``rp``, ``agno_vector``, ``fsiniestro``) se resuelve
    como en :func:`cnu_afiliado`.
    """
    x, u, h = edad_entera(x), edad_entera(u), _edad_hijo_opcional(h)
    agno_actual = _agno(agno_actual)
    tm_cot = tabla_mortalidad(tabla, ROL_AFILIADO, cot_mujer, fsiniestro, agno_actual, dir_tablas)
    tm_mp = tabla_mortalidad(tabla_benef, ROL_BENEFICIARIO, madre, fsiniestro, agno_actual, dir_tablas)
    qx_cot, qx_mp = tm_cot.qx_mejorado(agno_actual, x), tm_mp.qx_mejorado(agno_actual, u)
    tasas = tasas_por_periodo(agno_vector, rv, rp, dir_vectores, fsiniestro)
    encabezado = f"tablas {_etiqueta_tabla(tm_cot)} {_etiqueta_tabla(tm_mp)}"
    # Anualidad vitalicia de la madre o el padre condicionada al fallecimiento
    # del afiliado en el periodo (sin ajuste 11/24), como la del conyuge.
    vitalicia = _anualidad_bruta(qx_mp, u, tasas, EDAD_MAXIMA - u + 1, 0.0, qx_cot, x, pasos, encabezado)

    def temporal(periodos: int) -> float:
        return _anualidad_bruta(qx_mp, u, tasas, periodos, AJUSTE_MENSUAL, qx_cot, x, temporal=True)

    return _tramos_madre_padre(vitalicia, temporal, u, h, hijo_invalido, pasos)


def cnu_sobrevivencia_madre_padre(
    u: int,
    h: int | None = None,
    madre: bool = True,
    hijo_invalido: bool = False,
    tabla_benef: str = TABLA_BENEFICIARIO,
    agno_vector: int | None = AGNO_VECTOR,
    agno_actual: int | None = None,
    rv: float | None = None,
    rp: float | None = None,
    fsiniestro: int = 0,
    pasos: bool = False,
    dir_tablas=None,
    dir_vectores=None,
) -> float:
    """CNU de pension de sobrevivencia para la madre o el padre de hijos de
    filiacion no matrimonial (letras h, i y j del punto 1 del Anexo N 7). Sin
    rutina Mata equivalente.

    Con ``u`` la edad de la madre o el padre, ``h`` la del hijo menor no
    invalido con derecho, ``z = 24`` (:data:`EDAD_LIMITE_HIJO`) y ``u' = u + z
    - h``, el Anexo define, con la misma estructura que el conyuge
    (:func:`cnu_sobrevivencia_conyuge_con_hijos`):

    * letra h, sin hijos con derecho a pension (``h`` es ``None``), 36%
      (:data:`FRACCION_MADRE_PADRE`) vitalicio::

          cnu = 0,36 * [ sum_{t=0}^{w} l_{u+t} / (l_u (1+i_t)^t) - 11/24 ]

    * letra i, con hijos no invalidos con derecho, 30%
      (:data:`FRACCION_MADRE_PADRE_CON_HIJOS`) hasta ``u'`` y 36% despues::

          cnu = 0,30 * [ sum_{t=0}^{w} l_{u+t} / (l_u (1+i_t)^t) - 11/24 ]
                + 0,06 * [ sum_{t=0}^{w} l_{u'+t} / (l_u (1+i_{u'-u+t})^{u'-u+t})
                           - 11/24 * l_{u'} / (l_u (1+i_{u'-u})^{u'-u}) ]

      es decir, ``0,30 * temporal + 0,36 * (vitalicia - temporal)`` con la
      anualidad temporal hasta ``u'`` (ajuste temporal de
      :func:`cnu_sobrevivencia_hijo`). Con ``h >= 24`` coincide con la letra
      h; si la madre o el padre supera los 110 agnos antes de ``u'`` queda el
      30% vitalicio;

    * letra j, con algun hijo invalido con derecho (``hijo_invalido``), 30%
      vitalicio y ``h`` no interviene::

          cnu = 0,30 * [ sum_{t=0}^{w} l_{u+t} / (l_u (1+i_t)^t) - 11/24 ]

    :param u: edad de la madre o el padre de los hijos no matrimoniales.
    :param h: edad del hijo menor con derecho a pension (desde 0 agnos), o
        ``None`` (por defecto) si no hay hijos con derecho; se ignora con
        ``hijo_invalido``.
    :param madre: ``True`` (por defecto) si la beneficiaria es la madre;
        ``False`` si es el padre. Fija el sexo de la tabla de beneficiario.
    :param hijo_invalido: ``True`` si algun hijo con derecho es invalido (30%
        vitalicio, letra j).
    :param tabla_benef: tabla de mortalidad de la madre o el padre, con rol
        de beneficiario (p.ej. ``"b2006"``; por defecto ``"vigente"``).

    La tasa (``rv``, ``rp``, ``agno_vector``, ``fsiniestro``) se resuelve
    como en :func:`cnu_afiliado`.
    """
    u, h = edad_entera(u), _edad_hijo_opcional(h)
    agno_actual = _agno(agno_actual)
    tm = tabla_mortalidad(tabla_benef, ROL_BENEFICIARIO, madre, fsiniestro, agno_actual, dir_tablas)
    qx = tm.qx_mejorado(agno_actual, u)
    tasas = tasas_por_periodo(agno_vector, rv, rp, dir_vectores, fsiniestro)
    # Anualidad vitalicia de la madre o el padre menos el ajuste por pago
    # mensual, como la de cnu_sobrevivencia_conyuge.
    vitalicia = _anualidad_bruta(qx, u, tasas, EDAD_MAXIMA - u, AJUSTE_MENSUAL, pasos=pasos,
                                 encabezado=f"tabla {_etiqueta_tabla(tm)}")

    def temporal(periodos: int) -> float:
        return _anualidad_bruta(qx, u, tasas, periodos, AJUSTE_MENSUAL, temporal=True)

    return _tramos_madre_padre(vitalicia, temporal, u, h, hijo_invalido, pasos)


def cnu_padres(
    x: int,
    m: int,
    cot_mujer: bool = False,
    madre: bool = True,
    tabla: str = TABLA_AFILIADO,
    tabla_benef: str = TABLA_BENEFICIARIO,
    agno_vector: int | None = AGNO_VECTOR,
    agno_actual: int | None = None,
    rv: float | None = None,
    rp: float | None = None,
    fsiniestro: int = 0,
    pasos: bool = False,
    dir_tablas=None,
    dir_vectores=None,
) -> float:
    """CNU de la madre o el padre del afiliado pensionado por vejez o
    invalidez (letra l del punto 2 del Anexo N 7: madre o padre del
    causante). Sin rutina Mata equivalente.

    Con ``m`` la edad del padre o la madre, ``l`` los supervivientes de cada
    tabla e ``i_t`` la tasa del periodo ``t``, el Anexo define, con la misma
    estructura que el conyuge (:func:`cnu_conyuge`) y el 50%
    (:data:`FRACCION_PADRES`) del articulo 58 del D.L. N 3.500::

        cnu = 0,5 * sum_{t=0}^{w} l_{m+t} (1 - l_{x+t}/l_x) / (l_m (1+i_t)^t)

    Es la anualidad vitalicia del padre o la madre condicionada al
    fallecimiento del afiliado (``1 - l^x_t``), sin ajuste 11/24. Calcula a
    **uno** de los padres; con ambos, se llama una vez por cada uno (tabla de
    beneficiario del sexo que corresponda) y se suman los resultados al de
    :func:`cnu_afiliado`. Los padres solo tienen derecho a falta de conyuge,
    conviviente civil, hijos y madre o padre de hijos no matrimoniales, y
    siempre que sean carga familiar del afiliado; esa elegibilidad es un dato
    de entrada que no se valida aqui.

    :param x: edad del afiliado.
    :param m: edad del padre o la madre del afiliado.
    :param cot_mujer: ``True`` si el afiliado es mujer.
    :param madre: ``True`` (por defecto) si se calcula a la madre; ``False``
        si al padre. Fija el sexo de la tabla de beneficiario.
    :param tabla: tabla del afiliado (p.ej. ``"rv2009"``; por defecto ``"vigente"``).
    :param tabla_benef: tabla del padre o la madre, con rol de beneficiario
        (p.ej. ``"b2006"``; por defecto ``"vigente"``).

    La tasa (``rv``, ``rp``, ``agno_vector``, ``fsiniestro``) se resuelve
    como en :func:`cnu_afiliado`.
    """
    x, m = edad_entera(x), edad_entera(m)
    agno_actual = _agno(agno_actual)
    tm_cot = tabla_mortalidad(tabla, ROL_AFILIADO, cot_mujer, fsiniestro, agno_actual, dir_tablas)
    tm_padre = tabla_mortalidad(tabla_benef, ROL_BENEFICIARIO, madre, fsiniestro, agno_actual, dir_tablas)
    tasas = tasas_por_periodo(agno_vector, rv, rp, dir_vectores, fsiniestro)
    # 50% de la anualidad del padre o la madre condicionada al fallecimiento
    # del afiliado en el periodo; sin ajuste 11/24, como el conyuge.
    return anualidad(
        tm_padre.qx_mejorado(agno_actual, m), m, tasas, EDAD_MAXIMA - m + 1, FRACCION_PADRES, 0.0,
        tm_cot.qx_mejorado(agno_actual, x), x,
        pasos=pasos, encabezado=f"tablas {_etiqueta_tabla(tm_cot)} {_etiqueta_tabla(tm_padre)}",
    )


def cnu_sobrevivencia_padres(
    m: int,
    madre: bool = True,
    tabla_benef: str = TABLA_BENEFICIARIO,
    agno_vector: int | None = AGNO_VECTOR,
    agno_actual: int | None = None,
    rv: float | None = None,
    rp: float | None = None,
    fsiniestro: int = 0,
    pasos: bool = False,
    dir_tablas=None,
    dir_vectores=None,
) -> float:
    """CNU de pension de sobrevivencia para la madre o el padre del causante
    (letra k del punto 1 del Anexo N 7). Sin rutina Mata equivalente.

    Con ``m`` la edad del padre o la madre y ``l`` los supervivientes de la
    tabla de beneficiario de su sexo, el Anexo define, con la misma
    estructura que el conyuge (:func:`cnu_sobrevivencia_conyuge`) y el 50%
    (:data:`FRACCION_PADRES`) del articulo 58::

        cnu = 0,5 * [ sum_{t=0}^{w} l_{m+t} / (l_m (1+i_t)^t) - 11/24 ]

    Calcula a **uno** de los padres; con ambos, se llama una vez por cada
    uno y se suman los resultados. Su derecho (a falta de otros
    beneficiarios y como carga familiar del causante) es un dato de entrada.

    :param m: edad del padre o la madre del causante.
    :param madre: ``True`` (por defecto) si se calcula a la madre; ``False``
        si al padre. Fija el sexo de la tabla de beneficiario.
    :param tabla_benef: tabla de mortalidad del padre o la madre, con rol de
        beneficiario (p.ej. ``"b2006"``; por defecto ``"vigente"``).

    La tasa (``rv``, ``rp``, ``agno_vector``, ``fsiniestro``) se resuelve
    como en :func:`cnu_afiliado`.
    """
    m = edad_entera(m)
    agno_actual = _agno(agno_actual)
    tm = tabla_mortalidad(tabla_benef, ROL_BENEFICIARIO, madre, fsiniestro, agno_actual, dir_tablas)
    tasas = tasas_por_periodo(agno_vector, rv, rp, dir_vectores, fsiniestro)
    # 50% de la anualidad vitalicia del padre o la madre menos el ajuste por pago mensual.
    return anualidad(tm.qx_mejorado(agno_actual, m), m, tasas, EDAD_MAXIMA - m, FRACCION_PADRES, pasos=pasos,
                     encabezado=f"tabla {_etiqueta_tabla(tm)}")


def describir(
    tipo_cnu,
    tabla: str | None = None,
    tabla_benef: str | None = None,
    agno_vector: int | None = AGNO_VECTOR,
    agno_actual: int | None = None,
    rv: float | None = None,
    rp: float | None = None,
    fsiniestro: int = 0,
    mujer: bool = False,
    benef_mujer: bool = True,
    dir_tablas=None,
    rol_benef: str = ROL_BENEFICIARIO,
) -> str:
    """Etiqueta descriptiva del calculo, al estilo de los comandos de Stata.

    ``tipo_cnu`` es el nombre del calculo (``"soltero sin hijos"``, ``"hijo
    no inválido 15%"``) o el resultado de :func:`cnu.cnu_grupo_familiar`
    (:class:`cnu.CNUGrupoFamiliar`): en ese caso se nombra cada beneficiario
    con su porcentaje y se muestran las tablas resueltas por el grupo, e
    ``tabla`` y ``tabla_benef`` no intervienen.

    ``tabla`` es la del afiliado (sexo ``mujer``) y ``tabla_benef`` la del
    beneficiario (sexo ``benef_mujer`` y rol ``rol_benef``, por defecto
    :data:`ROL_BENEFICIARIO`; :data:`ROL_INVALIDO` para el hijo invalido).
    Se muestran las tablas efectivamente
    resueltas (tipo, agno y sexo), p.ej. ``cb2020h`` con ``fsiniestro`` de
    2024, y la tasa efectiva (``tasa 3.45%`` o ``vector 2013``, segun
    :func:`agno_vector_efectivo`); sin tasa determinable lanza el mismo
    ``ValueError`` que el calculo.
    """
    agno_actual = _agno(agno_actual)
    tablas = []
    if not isinstance(tipo_cnu, str):  # grupo familiar: etiqueta y tablas ya resueltas
        tablas, tipo_cnu = list(tipo_cnu.tablas), tipo_cnu.etiqueta
    else:
        for t, rol, es_mujer in ((tabla, ROL_AFILIADO, mujer), (tabla_benef, rol_benef, benef_mujer)):
            if t:
                tm = tabla_mortalidad(t, rol, es_mujer, fsiniestro, agno_actual, dir_tablas)
                tablas.append(_etiqueta_tabla(tm))
    etiqueta_tablas = ("tablas " if len(tablas) > 1 else "tabla ") + " ".join(tablas)
    if rv is not None:
        return f"CNU RV para {tipo_cnu} ({etiqueta_tablas}), tasa {rv * 100:g}% en el año {agno_actual}"
    if rp is not None:
        return f"CNU RP para {tipo_cnu} ({etiqueta_tablas}), tasa {rp * 100:g}% en el año {agno_actual}"
    agno_vector = agno_vector_efectivo(agno_vector, fsiniestro)
    return f"CNU RP para {tipo_cnu} ({etiqueta_tablas}), vector {agno_vector} en el año {agno_actual}"

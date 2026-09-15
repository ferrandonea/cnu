"""Compensacion por Diferencias de Expectativa de Vida (CEV) de la Ley N 21.735.

Beneficio para mujeres pensionadas regulado en la Letra C del Titulo XIX del
Libro III del Compendio de Normas del Sistema de Pensiones (Norma de Caracter
General N 350, de 12 de septiembre de 2025). :func:`calcular_cev` reutiliza
el CNU del grupo familiar (:func:`cnu.cnu_grupo_familiar`): el factor de
correccion es la razon entre el capital necesario del grupo con la tabla de
la mujer y el del mismo grupo con la tabla de un hombre de igual edad, con
las tablas vigentes a la fecha de pension.

Es un calculo referencial: la concesion y el pago los hace el Instituto de
Prevision Social (IPS) a partir del calculo de la AFP (Capitulo IV). Cubre el
flujo de pensionadas por vejez desde el 2 de enero de 2026 (letra b del
Capitulo III); el stock al 1 de enero de 2026 (letra a: PAFE y tablas al 1 de
abril de 2025) y la pension de invalidez (letra c: 100% sin escala por edad)
quedan fuera.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import core
from .core import TABLA_AFILIADO, TABLA_BENEFICIARIO
from .grupo import Afiliado, Beneficiario, CNUGrupoFamiliar, _a_beneficiario, cnu_grupo_familiar

# Vigencia del flujo (letra b del Capitulo III de la Letra C del Titulo XIX):
# afiliadas que se pensionan por vejez a partir del 2 de enero de 2026. Las
# pensionadas antes de esa fecha son el stock (letra a), fuera del alcance.
VIGENCIA_CEV = 20260102

# Letra b del Capitulo III: monto maximo de la anualidad CEV (pension de
# referencia) y monto minimo mensual del beneficio, ambos en UF.
TOPE_PENSION_REFERENCIA_UF = 18.0
MINIMO_CEV_UF = 0.25

# Edad desde la que se paga la compensacion y desde la que el porcentaje es 100%.
EDAD_CEV = 65

# Porcentaje de la compensacion segun la edad a la fecha de pension (tabla de
# beneficio del numero 2, letra b, del Capitulo II de la Letra C del Titulo
# XIX): 65 o mas agnos 100%, 64 75%, 63 50%, 62 25%, 61 15%, 60 5% y menos de
# 60 0% (sin recalculos posteriores por cumplimiento de agnos).
PORCENTAJE_CEV_POR_EDAD = {60: 0.05, 61: 0.15, 62: 0.25, 63: 0.50, 64: 0.75, EDAD_CEV: 1.0}
EDAD_MINIMA_CEV = min(PORCENTAJE_CEV_POR_EDAD)

_FUENTE = "Libro III, Titulo XIX, Letra C del Compendio de Normas del Sistema de Pensiones"


class ErrorCEV(ValueError):
    """La compensacion no corresponde (hombre, fecha de pension anterior a la
    vigencia, edad sin porcentaje, pension de referencia nula) o el caso no
    esta cubierto; el mensaje cita la regla."""


@dataclass
class ResultadoCEV:
    """Resultado de :func:`calcular_cev`.

    ``factor`` es la razon ``CNU mujer / CNU hombre`` del grupo familiar (el
    Compendio expresa el factor de correccion como esa razon menos 1, que
    aqui es :attr:`diferencia`); ``porcentaje`` la fraccion por edad de
    pension; ``pension_referencia`` la pension de referencia ya acotada a
    :data:`TOPE_PENSION_REFERENCIA_UF`; ``compensacion`` el producto
    ``pension_referencia x (factor - 1) x porcentaje`` antes del minimo, y
    ``monto`` el beneficio mensual en UF con dos decimales y el minimo
    :data:`MINIMO_CEV_UF` aplicado. ``grupo_mujer`` y ``grupo_hombre`` son
    los dos :class:`cnu.CNUGrupoFamiliar` con que se obtuvo el factor.
    """

    edad: int
    fecha_pension: int
    factor: float
    porcentaje: float
    pension_referencia: float
    compensacion: float
    monto: float
    grupo_mujer: CNUGrupoFamiliar
    grupo_hombre: CNUGrupoFamiliar
    descripcion: str = ""

    @property
    def diferencia(self) -> float:
        """Factor de correccion tal como lo escribe el Compendio: ``CNU mujer / CNU hombre - 1``."""
        return core._redondear(self.factor - 1)

    @property
    def cnu_mujer(self) -> float:
        return self.grupo_mujer.total

    @property
    def cnu_hombre(self) -> float:
        return self.grupo_hombre.total

    @property
    def minimo_aplicado(self) -> bool:
        """``True`` si el monto es el minimo de 0,25 UF porque la compensacion calculada era menor."""
        return self.compensacion < MINIMO_CEV_UF

    def to_dict(self) -> dict:
        return {
            "edad": self.edad, "fecha_pension": self.fecha_pension, "factor": self.factor,
            "diferencia": self.diferencia, "porcentaje": self.porcentaje,
            "pension_referencia": self.pension_referencia, "compensacion": self.compensacion, "monto": self.monto,
            "minimo_aplicado": self.minimo_aplicado, "cnu_mujer": self.cnu_mujer, "cnu_hombre": self.cnu_hombre,
            "descripcion": self.descripcion,
            "grupo_mujer": self.grupo_mujer.to_dict(), "grupo_hombre": self.grupo_hombre.to_dict(),
        }


def porcentaje_cev(edad: float) -> float:
    """Fraccion de la compensacion segun la edad (actuarial) a la fecha de pension.

    Tabla del Capitulo II, numero 2, letra b, de la Letra C del Titulo XIX del
    Libro III: 65 o mas agnos 1.0, 64 0.75, 63 0.5, 62 0.25, 61 0.15, 60 0.05.
    Menos de 60 agnos lanza :class:`ErrorCEV` (la tabla asigna 0% y la
    pension anticipada del articulo 68 del D.L. N 3.500 no da derecho).
    """
    e = core.edad_entera(edad)
    if e >= EDAD_CEV:
        return 1.0
    if e < EDAD_MINIMA_CEV:
        raise ErrorCEV(
            f"Edad de pension {e} menor que {EDAD_MINIMA_CEV}: la tabla de beneficio asigna 0% y la pension "
            f"anticipada del articulo 68 del D.L. N 3.500 no da derecho a la CEV (Capitulo II de la {_FUENTE})"
        )
    return PORCENTAJE_CEV_POR_EDAD[e]


def _validar(mujer: bool, fecha_pension, pension_referencia, rv) -> int:
    if not mujer:
        raise ErrorCEV(f"La CEV solo corresponde a mujeres (Capitulo II de la {_FUENTE})")
    if fecha_pension is None or core._es_missing(fecha_pension) or not int(fecha_pension):
        raise ErrorCEV("Debe entregarse la fecha de pension (YYYYMMDD): fija las tablas vigentes y la vigencia del beneficio")
    fecha = int(fecha_pension)
    if fecha < VIGENCIA_CEV:
        raise ErrorCEV(
            f"Fecha de pension {fecha} anterior a la vigencia del flujo de la CEV ({VIGENCIA_CEV}, letra b del "
            f"Capitulo III de la {_FUENTE}); el stock de pensionadas al 1 de enero de 2026 (letra a: PAFE y tablas "
            "al 1 de abril de 2025) no esta cubierto"
        )
    if pension_referencia is None or core._es_missing(pension_referencia) or float(pension_referencia) <= 0:
        raise ErrorCEV(
            "Pension de referencia (anualidad CEV) igual o menor que cero: no hay derecho al beneficio "
            f"(letra b del Capitulo III de la {_FUENTE})"
        )
    if rv is None or core._es_missing(rv):
        raise ErrorCEV(
            "Debe entregarse en rv la tasa de la anualidad: la tasa de interes promedio implicita de las rentas "
            "vitalicias de vejez de los seis meses anteriores a la fecha de pension, que publica la SP"
        )
    return fecha


def calcular_cev(
    edad: float,
    beneficiarios: list[Beneficiario | tuple | dict] = (),
    pension_referencia: float | None = None,
    fecha_pension: int | None = None,
    rv: float | None = None,
    mujer: bool = True,
    tabla: str = TABLA_AFILIADO,
    tabla_benef: str = TABLA_BENEFICIARIO,
    pasos: bool = False,
    dir_tablas=None,
    dir_vectores=None,
) -> ResultadoCEV:
    """Compensacion mensual por Diferencias de Expectativa de Vida (CEV) de
    una mujer que se pensiona por vejez, en UF.

    Letra b del Capitulo III de la Letra C del Titulo XIX del Libro III::

        CEV = pension_referencia x (CNU mujer / CNU hombre - 1) x porcentaje

    * **Factor de correccion**: razon entre el CNU del grupo familiar de la
      mujer (:func:`cnu.cnu_grupo_familiar` con ``Afiliado(edad, mujer=True)``)
      y el CNU del mismo grupo con la tabla de un hombre de igual edad
      (``mujer=False``), ambos con las tablas vigentes a ``fecha_pension``
      (``fsiniestro``) y con la tasa ``rv``. El Compendio llama factor de
      correccion a la razon menos 1 (:attr:`ResultadoCEV.diferencia`).
    * **Tasa**: la tasa de interes promedio implicita de las rentas
      vitalicias de vejez de los seis meses anteriores a la fecha de pension,
      que publica mensualmente la SP; la entrega el usuario en ``rv``.
    * **Porcentaje por edad**: :func:`porcentaje_cev` (100% a los 65 agnos,
      75% a los 64, 50% a los 63, 25% a los 62, 15% a los 61 y 5% a los 60),
      con la edad actuarial a la fecha de pension y sin recalculos
      posteriores.
    * **Tope y minimo**: la pension de referencia (anualidad CEV, la renta
      vitalicia inmediata simple que financia el saldo) se acota a
      :data:`TOPE_PENSION_REFERENCIA_UF` (18 UF) y el beneficio mensual no
      baja de :data:`MINIMO_CEV_UF` (0,25 UF); el monto se expresa en UF con
      dos decimales.

    Lanza :class:`ErrorCEV` (un ``ValueError``) si ``mujer`` es ``False``, si
    ``fecha_pension`` falta o es anterior a :data:`VIGENCIA_CEV` (20260102:
    el stock al 1 de enero de 2026 se calcula con la PAFE y no esta
    cubierto), si la edad es menor que 60 o si la pension de referencia es
    igual o menor que cero. La elegibilidad (cotizacion al Fondo Autonomo de
    Proteccion Previsional antes de los 50 agnos, pension sin cobertura del
    SIS, trabajos pesados) es un dato de entrada que no se valida; la pension
    de invalidez (letra c, 100% sin escala) no esta cubierta.

    :param edad: edad (actuarial) de la mujer a la fecha de pension.
    :param beneficiarios: grupo familiar con la misma estructura que
        :func:`cnu.cnu_grupo_familiar` (:class:`cnu.Beneficiario`, tuplas o
        diccionarios); el sexo de cada beneficiario se conserva en ambos CNU.
    :param pension_referencia: pension mensual de referencia en UF (anualidad
        CEV); se acota a 18 UF.
    :param fecha_pension: fecha de pension ``YYYYMMDD``.
    :param rv: tasa de la anualidad (tasa implicita promedio de rentas
        vitalicias de vejez de los ultimos seis meses).
    :param mujer: sexo de la persona; ``False`` lanza :class:`ErrorCEV`.
    :param pasos: imprime el calculo periodo a periodo de ambos grupos.
    """
    fecha = _validar(mujer, fecha_pension, pension_referencia, rv)
    e = core.edad_entera(edad)
    porcentaje = porcentaje_cev(e)
    beneficiarios = [_a_beneficiario(b) for b in beneficiarios]
    agno = fecha // 10000
    comunes = dict(tabla=tabla, tabla_benef=tabla_benef, agno_actual=agno, rv=rv, fsiniestro=fecha, pasos=pasos,
                   dir_tablas=dir_tablas, dir_vectores=dir_vectores)
    if pasos:
        print("=== CNU mujer ===")
    grupo_mujer = cnu_grupo_familiar(Afiliado(e, True), beneficiarios, **comunes)
    if pasos:
        print("=== CNU hombre de igual edad ===")
    grupo_hombre = cnu_grupo_familiar(Afiliado(e, False), beneficiarios, **comunes)
    factor = core._redondear(grupo_mujer.total / grupo_hombre.total)
    pension = min(float(pension_referencia), TOPE_PENSION_REFERENCIA_UF)
    compensacion = core._redondear(pension * (factor - 1) * porcentaje)
    monto = round(max(compensacion, MINIMO_CEV_UF), 2)
    grupo = ", ".join(c.etiqueta for c in grupo_mujer.componentes[1:]) or "sin beneficiarios"
    descripcion = (
        f"CEV para mujer de {e} años pensionada el {fecha}, grupo familiar: {grupo} "
        f"(tablas {' '.join(grupo_mujer.tablas)} / {' '.join(grupo_hombre.tablas)}), tasa {float(rv) * 100:g}%: "
        f"factor {factor:.6f}, {porcentaje * 100:g}% por edad"
    )
    return ResultadoCEV(e, fecha, factor, porcentaje, pension, compensacion, monto, grupo_mujer, grupo_hombre,
                        descripcion)


__all__ = ["EDAD_CEV", "MINIMO_CEV_UF", "PORCENTAJE_CEV_POR_EDAD", "TOPE_PENSION_REFERENCIA_UF", "VIGENCIA_CEV",
           "ErrorCEV", "ResultadoCEV", "calcular_cev", "porcentaje_cev"]

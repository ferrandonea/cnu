"""Grupo familiar completo del Anexo N 7: CNU total con el aporte de cada beneficiario.

:func:`cnu_grupo_familiar` recibe al afiliado (o ``None`` en sobrevivencia)
y la lista de beneficiarios (:class:`Beneficiario`), decide los tramos de
porcentaje del articulo 58 del D.L. N 3.500 a partir de los hijos con
derecho de la lista, valida las exclusiones del mismo articulo y devuelve un
:class:`CNUGrupoFamiliar` con el total, la lista de componentes y su
descripcion. Cada componente se calcula con la funcion escalar
correspondiente de :mod:`cnu.core`, de modo que el total es la suma exacta
de los valores individuales. La cuota mortuoria (:data:`CUOTA_MORTUORIA_UF`)
se agrega como componente opcional en las unidades del saldo.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import core
from .core import AGNO_VECTOR, EDAD_LIMITE_HIJO, TABLA_AFILIADO, TABLA_BENEFICIARIO

# Cuota mortuoria del articulo 88 del D.L. N 3.500: 15 UF que se retiran del
# saldo para cubrir los gastos del funeral del afiliado o pensionado.
CUOTA_MORTUORIA_UF = 15.0

# Tipos de beneficiario que admite el grupo familiar.
TIPO_CONYUGE = "conyuge"
TIPO_CONVIVIENTE = "conviviente"
TIPO_HIJO = "hijo"
TIPO_HIJO_INVALIDO = "hijo_invalido"
TIPO_MADRE_PADRE = "madre_padre"
TIPO_PADRES = "padres"
TIPOS_BENEFICIARIO = (TIPO_CONYUGE, TIPO_CONVIVIENTE, TIPO_HIJO, TIPO_HIJO_INVALIDO, TIPO_MADRE_PADRE, TIPO_PADRES)

# Sexo por defecto de cada tipo cuando ``Beneficiario.mujer`` es ``None``:
# el mismo de la funcion escalar correspondiente (``cony_mujer=True``,
# ``hijo_mujer=False``, ``madre=True``).
_MUJER_POR_DEFECTO = {
    TIPO_CONYUGE: True, TIPO_CONVIVIENTE: True, TIPO_HIJO: False, TIPO_HIJO_INVALIDO: False,
    TIPO_MADRE_PADRE: True, TIPO_PADRES: True,
}

ARTICULO_58 = "articulo 58 del D.L. N 3.500"


class ErrorGrupoFamiliar(ValueError):
    """Grupo familiar que la norma no admite (exclusiones del articulo 58) o
    que el paquete no cubre; el mensaje cita la regla."""


@dataclass(frozen=True)
class Afiliado:
    """Afiliado o causante vivo (pension de vejez o invalidez)."""

    edad: float
    mujer: bool = False


@dataclass(frozen=True)
class Beneficiario:
    """Un beneficiario del grupo familiar.

    :param tipo: uno de :data:`TIPOS_BENEFICIARIO`: ``"conyuge"``,
        ``"conviviente"`` (civil, misma formula que el conyuge), ``"hijo"``
        (no invalido, con derecho hasta los 24 agnos), ``"hijo_invalido"``,
        ``"madre_padre"`` (de hijos de filiacion no matrimonial) o
        ``"padres"`` (madre o padre del afiliado, uno por registro).
    :param edad: edad (actuarial) del beneficiario; los hijos desde 0.
    :param mujer: sexo, que fija la tabla de beneficiario; ``None`` usa el
        sexo por defecto del tipo (conyuge y conviviente mujer, hijos hombre,
        madre para ``"madre_padre"`` y ``"padres"``). En ``"madre_padre"`` y
        ``"padres"``, ``True`` es la madre y ``False`` el padre.
    :param parcial: solo para ``"hijo_invalido"``: ``True`` si la invalidez
        es parcial (15% hasta los 24 y 11% despues); ``False`` total.
    """

    tipo: str
    edad: float
    mujer: bool | None = None
    parcial: bool = False

    @property
    def es_mujer(self) -> bool:
        return _MUJER_POR_DEFECTO[self.tipo] if self.mujer is None else bool(self.mujer)


@dataclass(frozen=True)
class ComponenteCNU:
    """Aporte de un miembro del grupo (o de la cuota mortuoria) al CNU total.

    ``porcentajes`` son las fracciones del articulo 58 aplicadas en orden de
    tramos (p.ej. ``(0.5, 0.6)`` para el conyuge con hijos), ``etiqueta`` el
    tipo de beneficiario y el porcentaje en texto (``"cónyuge con hijos
    50%/60%"``) y ``tablas`` las tablas de mortalidad resueltas.
    """

    tipo: str
    etiqueta: str
    porcentajes: tuple[float, ...]
    cnu: float
    tablas: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"tipo": self.tipo, "etiqueta": self.etiqueta, "porcentajes": list(self.porcentajes),
                "cnu": self.cnu, "tablas": list(self.tablas)}


@dataclass
class CNUGrupoFamiliar:
    """Resultado de :func:`cnu_grupo_familiar`: ``total`` es la suma exacta
    de ``componentes`` (redondeada a seis decimales)."""

    total: float
    componentes: list[ComponenteCNU]
    descripcion: str = ""
    sobrevivencia: bool = False

    @property
    def etiqueta(self) -> str:
        """Nombre del grupo con cada beneficiario y su porcentaje, para :func:`cnu.describir`."""
        quien = "sobrevivencia de grupo familiar" if self.sobrevivencia else "grupo familiar"
        return f"{quien}: " + ", ".join(c.etiqueta for c in self.componentes)

    @property
    def tablas(self) -> tuple[str, ...]:
        """Tablas de mortalidad resueltas por los componentes, sin repetir y en orden."""
        return tuple(dict.fromkeys(t for c in self.componentes for t in c.tablas))

    def to_dict(self) -> dict:
        return {"total": self.total, "descripcion": self.descripcion, "sobrevivencia": self.sobrevivencia,
                "componentes": [c.to_dict() for c in self.componentes]}


def etiqueta_hijo_invalido(parcial: bool) -> str:
    """Tipo de beneficiario y porcentaje aplicado para ``describir``."""
    return "hijo inválido parcial 15%/11%" if parcial else "hijo inválido total 15%"


def etiqueta_conyuge(conviviente: bool, con_hijos: bool = False, hijo_invalido: bool = False) -> str:
    """Tipo de beneficiario (cónyuge o conviviente civil) y porcentaje aplicado para ``describir``."""
    quien = "conviviente civil" if conviviente else "cónyuge"
    if not con_hijos:
        return f"{quien} sin hijos"
    return f"{quien} con hijo inválido 50%" if hijo_invalido else f"{quien} con hijos 50%/60%"


def etiqueta_madre_padre(madre: bool, h=None, hijo_invalido: bool = False) -> str:
    """Madre o padre de hijos no matrimoniales y porcentaje aplicado para ``describir``."""
    quien = "madre" if madre else "padre"
    if hijo_invalido:
        return f"{quien} no matrimonial con hijo inválido 30%"
    if h is None or core.edad_entera(h) >= EDAD_LIMITE_HIJO:
        return f"{quien} no matrimonial sin hijos 36%"
    return f"{quien} no matrimonial con hijos 30%/36%"


def etiqueta_padres(madre: bool, de: str = "del afiliado") -> str:
    """Madre o padre del afiliado (o del causante) y porcentaje aplicado para ``describir``."""
    return f"{'madre' if madre else 'padre'} {de} 50%"


def _a_afiliado(afiliado) -> Afiliado | None:
    if afiliado is None or isinstance(afiliado, Afiliado):
        return afiliado
    if isinstance(afiliado, (tuple, list)):
        return Afiliado(*afiliado)
    if isinstance(afiliado, dict):
        return Afiliado(**afiliado)
    return Afiliado(afiliado)


def _a_beneficiario(b) -> Beneficiario:
    if isinstance(b, Beneficiario):
        return b
    if isinstance(b, dict):
        return Beneficiario(**b)
    return Beneficiario(*b)


def _validar(afiliado: Afiliado | None, beneficiarios: list[Beneficiario]) -> None:
    """Exclusiones del articulo 58 del D.L. N 3.500 y casos que el paquete no cubre."""
    for b in beneficiarios:
        if b.tipo not in TIPOS_BENEFICIARIO:
            raise ErrorGrupoFamiliar(
                f"Tipo de beneficiario desconocido: {b.tipo!r}; los tipos admitidos son {', '.join(TIPOS_BENEFICIARIO)}"
            )
        if b.parcial and b.tipo != TIPO_HIJO_INVALIDO:
            raise ErrorGrupoFamiliar(f"El grado de invalidez (parcial) solo aplica al hijo invalido, no a {b.tipo!r}")
    tipos = [b.tipo for b in beneficiarios]
    if afiliado is None and not beneficiarios:
        raise ErrorGrupoFamiliar("Pension de sobrevivencia (afiliado None) sin beneficiarios: no hay CNU que calcular")
    n_pareja = tipos.count(TIPO_CONYUGE) + tipos.count(TIPO_CONVIVIENTE)
    if n_pareja > 1:
        raise ErrorGrupoFamiliar(
            f"El grupo admite a lo mas un conyuge o un conviviente civil ({ARTICULO_58}; el acuerdo de union civil "
            "de la Ley N 20.830 exige no estar casado)"
        )
    padres = [b for b in beneficiarios if b.tipo == TIPO_PADRES]
    if padres:
        otros = sorted({t for t in tipos if t != TIPO_PADRES})
        if otros:
            raise ErrorGrupoFamiliar(
                f"Los padres del afiliado solo tienen derecho a falta de conyuge, conviviente civil, hijos y madre o "
                f"padre de hijos no matrimoniales ({ARTICULO_58}); el grupo incluye {', '.join(otros)}"
            )
        if sum(b.es_mujer for b in padres) > 1 or sum(not b.es_mujer for b in padres) > 1:
            raise ErrorGrupoFamiliar(f"El grupo admite a lo mas una madre y un padre del afiliado ({ARTICULO_58})")
    con_derecho = any(b.tipo == TIPO_HIJO_INVALIDO or (b.tipo == TIPO_HIJO and core.edad_entera(b.edad) < EDAD_LIMITE_HIJO)
                      for b in beneficiarios)
    if con_derecho and n_pareja == 0 and TIPO_MADRE_PADRE not in tipos:
        raise ErrorGrupoFamiliar(
            "Hijos con derecho a pension sin conyuge, conviviente civil ni madre o padre de hijos no matrimoniales: "
            f"su porcentaje es 0,15 + 0,5/n ({ARTICULO_58}; letras 1.f, 1.g, 2.g y 2.h del Anexo N 7), "
            "caso que el paquete no cubre"
        )


def _tablas(afiliado: Afiliado | None, benef: Beneficiario | None, rol_benef: str, tabla, tabla_benef,
            fsiniestro, agno_actual, dir_tablas) -> tuple[str, ...]:
    """Etiquetas de las tablas resueltas (afiliado y beneficiario), en el orden de la funcion escalar."""
    etiquetas = []
    if afiliado is not None:
        tm = core.tabla_mortalidad(tabla, core.ROL_AFILIADO, afiliado.mujer, fsiniestro, agno_actual, dir_tablas)
        etiquetas.append(core._etiqueta_tabla(tm))
    if benef is not None:
        tm = core.tabla_mortalidad(tabla_benef, rol_benef, benef.es_mujer, fsiniestro, agno_actual, dir_tablas)
        etiquetas.append(core._etiqueta_tabla(tm))
    return tuple(etiquetas)


def cnu_grupo_familiar(
    afiliado: Afiliado | tuple | float | None,
    beneficiarios: list[Beneficiario | tuple | dict] = (),
    valor_uf: float | None = None,
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
) -> CNUGrupoFamiliar:
    """CNU total de un grupo familiar del Anexo N 7 con el aporte de cada
    beneficiario, sin componer los porcentajes a mano.

    Con afiliado (pension de vejez o invalidez) el grupo suma
    :func:`cnu.cnu_afiliado` y las funciones de cada beneficiario
    (:func:`cnu.cnu_conyuge`, :func:`cnu.cnu_conyuge_con_hijos`,
    :func:`cnu.cnu_hijo`, :func:`cnu.cnu_hijo_invalido`,
    :func:`cnu.cnu_madre_padre`, :func:`cnu.cnu_padres`); con ``afiliado``
    ``None`` (pension de sobrevivencia) usa las variantes
    ``cnu_sobrevivencia_*``. El total es la suma exacta de los componentes.

    Los tramos de porcentaje del articulo 58 del D.L. N 3.500 se deciden
    desde la lista: el hijo menor no invalido con derecho (menor de 24 agnos)
    fija el cambio 50%/60% del conyuge o conviviente y 30%/36% de la madre o
    el padre no matrimonial; algun hijo invalido los deja en 50% y 30%
    vitalicios; sin hijos con derecho quedan en 60% y 36%. Todos los hijos
    de la lista cuentan para todos los beneficiarios cuyo porcentaje depende
    de ellos.

    Exclusiones que lanzan :class:`ErrorGrupoFamiliar` (un ``ValueError``
    que cita el articulo 58): padres del afiliado junto con conyuge,
    conviviente civil, hijos o madre o padre no matrimonial; mas de un
    conyuge o conviviente; mas de una madre o un padre del afiliado; tipo de
    beneficiario desconocido; sobrevivencia sin beneficiarios. Tambien falla
    el grupo con hijos con derecho pero sin conyuge, conviviente ni madre o
    padre no matrimonial, cuyo porcentaje ``0,15 + 0,5/n`` (letras 1.f, 1.g,
    2.g y 2.h) no esta cubierto. La elegibilidad de cada beneficiario (calidad
    de estudiante, invalidez declarada, union civil, carga familiar de los
    padres) es un dato de entrada que no se valida.

    :param afiliado: :class:`Afiliado` (edad y sexo), una tupla ``(edad,
        mujer)``, una edad (hombre) o ``None`` en sobrevivencia.
    :param beneficiarios: lista de :class:`Beneficiario` (o tuplas ``(tipo,
        edad[, mujer[, parcial]])`` o diccionarios con esos campos).
    :param valor_uf: valor de la UF en las unidades del saldo; si se
        entrega, se agrega la cuota mortuoria (:data:`CUOTA_MORTUORIA_UF`,
        15 UF) como componente separado, ``15 * valor_uf``, y el total pasa a
        ser el capital necesario para una pension de 1 en esas unidades.
    :param tabla: tabla del afiliado (por defecto ``"vigente"``).
    :param tabla_benef: tabla de los beneficiarios (por defecto
        ``"vigente"``, resuelta por rol y sexo de cada uno: ``b`` o ``cb``
        para beneficiarios y ``mi`` para hijos invalidos).
    :param pasos: imprime el calculo periodo a periodo de cada componente.

    La tasa (``rv``, ``rp``, ``agno_vector``, ``fsiniestro``) se resuelve
    como en :func:`cnu.cnu_afiliado`.
    """
    afiliado = _a_afiliado(afiliado)
    beneficiarios = [_a_beneficiario(b) for b in beneficiarios]
    _validar(afiliado, beneficiarios)
    agno_actual = core._agno(agno_actual)
    comunes = dict(agno_vector=agno_vector, agno_actual=agno_actual, rv=rv, rp=rp, fsiniestro=fsiniestro,
                   pasos=pasos, dir_tablas=dir_tablas, dir_vectores=dir_vectores)
    tablas_de = dict(tabla=tabla, tabla_benef=tabla_benef, fsiniestro=fsiniestro, agno_actual=agno_actual,
                     dir_tablas=dir_tablas)
    sobrev = afiliado is None

    # Hijos con derecho de la lista: fijan los tramos de conyuge y madre o padre.
    hijo_invalido = any(b.tipo == TIPO_HIJO_INVALIDO for b in beneficiarios)
    edades_hijos = [core.edad_entera(b.edad) for b in beneficiarios if b.tipo == TIPO_HIJO]
    con_derecho = [h for h in edades_hijos if h < EDAD_LIMITE_HIJO]
    h_menor = min(con_derecho) if con_derecho else None
    con_hijos = hijo_invalido or h_menor is not None

    componentes: list[ComponenteCNU] = []

    def agregar(tipo, etiqueta, porcentajes, fn, benef, rol_benef, *args, **kwargs):
        if pasos:
            print(f"--- {etiqueta} ---")
        valor = fn(*args, **kwargs, **comunes)
        tablas = _tablas(afiliado, benef, rol_benef, **tablas_de)
        componentes.append(ComponenteCNU(tipo, etiqueta, tuple(porcentajes), valor, tablas))

    if not sobrev:
        x = afiliado.edad
        agregar("afiliado", "afiliado", (1.0,), core.cnu_afiliado, None, None, x, afiliado.mujer, tabla)

    for b in beneficiarios:
        if b.tipo in (TIPO_CONYUGE, TIPO_CONVIVIENTE):
            conviviente = b.tipo == TIPO_CONVIVIENTE
            etiqueta = etiqueta_conyuge(conviviente, con_hijos, hijo_invalido)
            if not con_hijos:
                porcentajes = (core.FRACCION_CONYUGE,)
                if sobrev:
                    agregar(b.tipo, etiqueta, porcentajes, core.cnu_sobrevivencia_conyuge, b, core.ROL_BENEFICIARIO,
                            b.edad, b.es_mujer, tabla_benef, conviviente=conviviente)
                else:
                    agregar(b.tipo, etiqueta, porcentajes, core.cnu_conyuge, b, core.ROL_BENEFICIARIO,
                            x, b.edad, afiliado.mujer, b.es_mujer, tabla, tabla_benef, conviviente=conviviente)
            else:
                porcentajes = (core.FRACCION_CONYUGE_CON_HIJOS,) if hijo_invalido else (
                    core.FRACCION_CONYUGE_CON_HIJOS, core.FRACCION_CONYUGE)
                h = 0 if h_menor is None else h_menor  # con hijo_invalido la edad h no interviene
                if sobrev:
                    agregar(b.tipo, etiqueta, porcentajes, core.cnu_sobrevivencia_conyuge_con_hijos, b,
                            core.ROL_BENEFICIARIO, b.edad, h, b.es_mujer, hijo_invalido, tabla_benef,
                            conviviente=conviviente)
                else:
                    agregar(b.tipo, etiqueta, porcentajes, core.cnu_conyuge_con_hijos, b, core.ROL_BENEFICIARIO,
                            x, b.edad, h, afiliado.mujer, b.es_mujer, hijo_invalido, tabla, tabla_benef,
                            conviviente=conviviente)
        elif b.tipo == TIPO_HIJO:
            sin_derecho = core.edad_entera(b.edad) >= EDAD_LIMITE_HIJO
            etiqueta = f"hijo no inválido sin derecho ({EDAD_LIMITE_HIJO} años o más)" if sin_derecho else "hijo no inválido 15%"
            porcentajes = (0.0,) if sin_derecho else (core.FRACCION_HIJO,)
            if sobrev:
                agregar(b.tipo, etiqueta, porcentajes, core.cnu_sobrevivencia_hijo, b, core.ROL_BENEFICIARIO,
                        b.edad, b.es_mujer, tabla_benef)
            else:
                agregar(b.tipo, etiqueta, porcentajes, core.cnu_hijo, b, core.ROL_BENEFICIARIO,
                        x, b.edad, afiliado.mujer, b.es_mujer, tabla, tabla_benef)
        elif b.tipo == TIPO_HIJO_INVALIDO:
            etiqueta = etiqueta_hijo_invalido(b.parcial)
            if not b.parcial:
                porcentajes = (core.FRACCION_HIJO,)
            elif core.edad_entera(b.edad) >= EDAD_LIMITE_HIJO:
                porcentajes = (core.FRACCION_HIJO_INVALIDO_PARCIAL,)
            else:
                porcentajes = (core.FRACCION_HIJO, core.FRACCION_HIJO_INVALIDO_PARCIAL)
            if sobrev:
                agregar(b.tipo, etiqueta, porcentajes, core.cnu_sobrevivencia_hijo_invalido, b, core.ROL_INVALIDO,
                        b.edad, b.es_mujer, b.parcial, tabla_benef)
            else:
                agregar(b.tipo, etiqueta, porcentajes, core.cnu_hijo_invalido, b, core.ROL_INVALIDO,
                        x, b.edad, afiliado.mujer, b.es_mujer, b.parcial, tabla, tabla_benef)
        elif b.tipo == TIPO_MADRE_PADRE:
            etiqueta = etiqueta_madre_padre(b.es_mujer, h_menor, hijo_invalido)
            if hijo_invalido:
                porcentajes = (core.FRACCION_MADRE_PADRE_CON_HIJOS,)
            elif h_menor is None:
                porcentajes = (core.FRACCION_MADRE_PADRE,)
            else:
                porcentajes = (core.FRACCION_MADRE_PADRE_CON_HIJOS, core.FRACCION_MADRE_PADRE)
            if sobrev:
                agregar(b.tipo, etiqueta, porcentajes, core.cnu_sobrevivencia_madre_padre, b, core.ROL_BENEFICIARIO,
                        b.edad, h_menor, b.es_mujer, hijo_invalido, tabla_benef)
            else:
                agregar(b.tipo, etiqueta, porcentajes, core.cnu_madre_padre, b, core.ROL_BENEFICIARIO,
                        x, b.edad, h_menor, afiliado.mujer, b.es_mujer, hijo_invalido, tabla, tabla_benef)
        elif b.tipo == TIPO_PADRES:
            etiqueta = etiqueta_padres(b.es_mujer, "del causante" if sobrev else "del afiliado")
            porcentajes = (core.FRACCION_PADRES,)
            if sobrev:
                agregar(b.tipo, etiqueta, porcentajes, core.cnu_sobrevivencia_padres, b, core.ROL_BENEFICIARIO,
                        b.edad, b.es_mujer, tabla_benef)
            else:
                agregar(b.tipo, etiqueta, porcentajes, core.cnu_padres, b, core.ROL_BENEFICIARIO,
                        x, b.edad, afiliado.mujer, b.es_mujer, tabla, tabla_benef)

    if valor_uf is not None:
        cuota = core._redondear(CUOTA_MORTUORIA_UF * float(valor_uf))
        if pasos:
            print(f"--- cuota mortuoria: {CUOTA_MORTUORIA_UF:g} UF * {float(valor_uf):g} = {cuota:g} ---")
        componentes.append(ComponenteCNU("cuota_mortuoria", f"cuota mortuoria {CUOTA_MORTUORIA_UF:g} UF", (), cuota))

    resultado = CNUGrupoFamiliar(core._redondear(sum(c.cnu for c in componentes)), componentes, sobrevivencia=sobrev)
    resultado.descripcion = core.describir(resultado, agno_vector=agno_vector, agno_actual=agno_actual, rv=rv, rp=rp,
                                           fsiniestro=fsiniestro)
    return resultado

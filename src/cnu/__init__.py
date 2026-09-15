"""cnu: Calculador del Capital Necesario Unitario (CNU) del sistema de pensiones chileno.

Conversion a Python del modulo de Stata/Mata ``cnu`` de George G. Vega Yon
(Superintendencia de Pensiones).

Funciones principales
---------------------
* :func:`cnu_afiliado`, :func:`cnu_conyuge`, :func:`cnu_sobrevivencia_conyuge`:
  CNU escalar (comandos ``cnu_afili``, ``cnu_cnyg_s_hi``, ``cnu_sobr_cnyg_s_hi``).
* :func:`cnu_hijo`, :func:`cnu_sobrevivencia_hijo`: hijo no invalido (15%,
  hasta los 24 agnos), sin comando Mata equivalente.
* :func:`cnu_hijo_invalido`, :func:`cnu_sobrevivencia_hijo_invalido`: hijo
  invalido total (15% vitalicio) o parcial (15% hasta los 24 y 11% despues),
  con tabla de invalidos, sin comando Mata equivalente.
* :func:`cnu_conyuge_con_hijos`, :func:`cnu_sobrevivencia_conyuge_con_hijos`:
  conyuge con hijos con derecho a pension (50% mientras el hijo menor tenga
  derecho y 60% despues; 50% vitalicio con algun hijo invalido), sin comando
  Mata equivalente. El conviviente civil usa las funciones del conyuge con
  ``conviviente=True`` (misma formula).
* :func:`cnu_madre_padre`, :func:`cnu_sobrevivencia_madre_padre`: madre o
  padre de hijos de filiacion no matrimonial (36% sin hijos con derecho, 30%
  mientras los haya), sin comando Mata equivalente.
* :func:`cnu_padres`, :func:`cnu_sobrevivencia_padres`: madre o padre del
  afiliado (50% cada uno, a falta de otros beneficiarios), sin comando Mata
  equivalente.
* :func:`cnu_grupo_familiar`: CNU total de un grupo familiar (afiliado o
  ``None`` en sobrevivencia mas una lista de :class:`Beneficiario`) con el
  aporte de cada beneficiario (:class:`CNUGrupoFamiliar`), tramos del
  articulo 58 decididos desde la lista, validacion de sus exclusiones
  (:class:`ErrorGrupoFamiliar`) y cuota mortuoria opcional
  (:data:`CUOTA_MORTUORIA_UF`).
* :func:`cnu_afiliado_vec`, :func:`cnu_conyuge_vec`,
  :func:`cnu_sobrevivencia_conyuge_vec`, :func:`cnu_hijo_vec`,
  :func:`cnu_sobrevivencia_hijo_vec`, :func:`cnu_hijo_invalido_vec`,
  :func:`cnu_sobrevivencia_hijo_invalido_vec`, :func:`cnu_conyuge_con_hijos_vec`,
  :func:`cnu_sobrevivencia_conyuge_con_hijos_vec`, :func:`cnu_madre_padre_vec`,
  :func:`cnu_sobrevivencia_madre_padre_vec`, :func:`cnu_padres_vec`,
  :func:`cnu_sobrevivencia_padres_vec`: versiones vectoriales
  (``cnu_afil``, ...).
* :func:`cnu_grupo_familiar_vec`: grupo familiar de cada fila (afiliado,
  conyuge o conviviente y hasta ``k`` hijos por columnas, con sexo y grado de
  invalidez :data:`GRADO_NO_INVALIDO`, :data:`GRADO_INVALIDO_TOTAL` o
  :data:`GRADO_INVALIDO_PARCIAL`), total por fila y matriz opcional de
  componentes.
* :func:`proyectar_cnu`, :func:`proyectar_pension`: proyecciones (``cnu_proy_pensi``);
  la trayectoria de pension aplica la banda de variacion maxima del 10% de la
  Ley N 21.735 desde :data:`VIGENCIA_BANDA` (parametro ``banda`` y
  :func:`banda_vigente`).
* :func:`faj_afiliado`, :func:`faj_afiliado_vec`, :func:`calcular_faj`:
  Factor de Ajuste (``cnu_faji``, ``cnu_faj``), derogado desde el 1 de
  febrero de 2022 (:data:`DEROGACION_FAJ`; solo para calculos historicos).
"""

__version__ = "0.3.0"

from .core import (  # noqa: E402
    AGNO_VECTOR,
    AJUSTE_MENSUAL,
    EDAD_LIMITE_HIJO,
    EDAD_MAXIMA,
    EDAD_MINIMA,
    EDAD_MINIMA_HIJO,
    FRACCION_CONYUGE,
    FRACCION_CONYUGE_CON_HIJOS,
    FRACCION_HIJO,
    FRACCION_HIJO_INVALIDO_PARCIAL,
    FRACCION_MADRE_PADRE,
    FRACCION_MADRE_PADRE_CON_HIJOS,
    FRACCION_PADRES,
    INICIO_TITRP,
    ROL_AFILIADO,
    ROL_BENEFICIARIO,
    ROL_INVALIDO,
    TABLA_AFILIADO,
    TABLA_BENEFICIARIO,
    TABLA_VIGENTE,
    agno_vector_efectivo,
    cnu_afiliado,
    cnu_conyuge,
    cnu_conyuge_con_hijos,
    cnu_hijo,
    cnu_hijo_invalido,
    cnu_madre_padre,
    cnu_padres,
    cnu_sobrevivencia_conyuge,
    cnu_sobrevivencia_conyuge_con_hijos,
    cnu_sobrevivencia_hijo,
    cnu_sobrevivencia_hijo_invalido,
    cnu_sobrevivencia_madre_padre,
    cnu_sobrevivencia_padres,
    describir,
    edad_actuarial,
    edad_entera,
    tabla_mortalidad,
    tasas_por_periodo,
)
from .faj import (  # noqa: E402
    DEROGACION_FAJ,
    calcular_faj,
    faj_afiliado,
    faj_afiliado_vec,
    faj_derogado,
    faj_funcion_objetivo,
)
from .grupo import (  # noqa: E402
    CUOTA_MORTUORIA_UF,
    TIPOS_BENEFICIARIO,
    Afiliado,
    Beneficiario,
    CNUGrupoFamiliar,
    ComponenteCNU,
    ErrorGrupoFamiliar,
    cnu_grupo_familiar,
)
from .proyeccion import (  # noqa: E402
    BANDA_VARIACION,
    VIGENCIA_BANDA,
    ProyeccionPension,
    banda_vigente,
    proyectar_cnu,
    proyectar_pension,
)
from .tablas import (  # noqa: E402
    TablaMortalidad,
    agno_tabla_por_siniestro,
    cargar_tabla_mortalidad,
    cargar_vector_tasas,
    escribir_matriz_mata,
    guardar_tabla_mortalidad,
    guardar_vector_tasas,
    leer_matriz_mata,
    tabla_por_fecha,
    tablas_disponibles,
    vectores_disponibles,
)
from .vectorial import (  # noqa: E402
    GRADO_INVALIDO_PARCIAL,
    GRADO_INVALIDO_TOTAL,
    GRADO_NO_INVALIDO,
    GRADOS_INVALIDEZ,
    AdvertenciaCNU,
    cnu_afiliado_vec,
    cnu_conyuge_con_hijos_vec,
    cnu_conyuge_vec,
    cnu_grupo_familiar_vec,
    cnu_hijo_invalido_vec,
    cnu_hijo_vec,
    cnu_madre_padre_vec,
    cnu_padres_vec,
    cnu_sobrevivencia_conyuge_con_hijos_vec,
    cnu_sobrevivencia_conyuge_vec,
    cnu_sobrevivencia_hijo_invalido_vec,
    cnu_sobrevivencia_hijo_vec,
    cnu_sobrevivencia_madre_padre_vec,
    cnu_sobrevivencia_padres_vec,
)


def main() -> None:
    """Punto de entrada del comando ``cnu``."""
    import sys

    from .cli import main as _main

    sys.exit(_main())


__all__ = [
    "AGNO_VECTOR", "AJUSTE_MENSUAL", "BANDA_VARIACION", "CUOTA_MORTUORIA_UF", "DEROGACION_FAJ", "EDAD_LIMITE_HIJO", "EDAD_MAXIMA", "EDAD_MINIMA",
    "EDAD_MINIMA_HIJO",
    "FRACCION_CONYUGE", "FRACCION_CONYUGE_CON_HIJOS", "FRACCION_HIJO", "FRACCION_HIJO_INVALIDO_PARCIAL",
    "FRACCION_MADRE_PADRE", "FRACCION_MADRE_PADRE_CON_HIJOS", "FRACCION_PADRES",
    "GRADO_INVALIDO_PARCIAL", "GRADO_INVALIDO_TOTAL", "GRADO_NO_INVALIDO", "GRADOS_INVALIDEZ", "INICIO_TITRP",
    "ROL_AFILIADO", "ROL_BENEFICIARIO", "ROL_INVALIDO",
    "TABLA_AFILIADO", "TABLA_BENEFICIARIO", "TABLA_VIGENTE", "TIPOS_BENEFICIARIO", "VIGENCIA_BANDA",
    "AdvertenciaCNU", "Afiliado", "Beneficiario", "CNUGrupoFamiliar", "ComponenteCNU", "ErrorGrupoFamiliar",
    "ProyeccionPension", "TablaMortalidad",
    "agno_tabla_por_siniestro", "agno_vector_efectivo", "banda_vigente", "calcular_faj", "cargar_tabla_mortalidad", "cargar_vector_tasas",
    "cnu_afiliado", "cnu_afiliado_vec", "cnu_conyuge", "cnu_conyuge_con_hijos", "cnu_conyuge_con_hijos_vec",
    "cnu_conyuge_vec", "cnu_grupo_familiar", "cnu_grupo_familiar_vec", "cnu_hijo", "cnu_hijo_invalido", "cnu_hijo_invalido_vec", "cnu_hijo_vec",
    "cnu_madre_padre", "cnu_madre_padre_vec", "cnu_padres", "cnu_padres_vec",
    "cnu_sobrevivencia_conyuge", "cnu_sobrevivencia_conyuge_con_hijos", "cnu_sobrevivencia_conyuge_con_hijos_vec",
    "cnu_sobrevivencia_conyuge_vec", "cnu_sobrevivencia_hijo",
    "cnu_sobrevivencia_hijo_invalido", "cnu_sobrevivencia_hijo_invalido_vec",
    "cnu_sobrevivencia_hijo_vec", "cnu_sobrevivencia_madre_padre", "cnu_sobrevivencia_madre_padre_vec",
    "cnu_sobrevivencia_padres", "cnu_sobrevivencia_padres_vec", "describir", "edad_actuarial", "edad_entera",
    "escribir_matriz_mata", "faj_afiliado", "faj_afiliado_vec", "faj_derogado", "faj_funcion_objetivo",
    "guardar_tabla_mortalidad", "guardar_vector_tasas", "leer_matriz_mata", "main",
    "proyectar_cnu", "proyectar_pension", "tabla_mortalidad", "tabla_por_fecha", "tablas_disponibles",
    "tasas_por_periodo",
    "vectores_disponibles",
]

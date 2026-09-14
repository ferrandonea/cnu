"""cnu: Calculador del Capital Necesario Unitario (CNU) del sistema de pensiones chileno.

Conversion a Python del modulo de Stata/Mata ``cnu`` de George G. Vega Yon
(Superintendencia de Pensiones).

Funciones principales
---------------------
* :func:`cnu_afiliado`, :func:`cnu_conyuge`, :func:`cnu_sobrevivencia_conyuge`:
  CNU escalar (comandos ``cnu_afili``, ``cnu_cnyg_s_hi``, ``cnu_sobr_cnyg_s_hi``).
* :func:`cnu_afiliado_vec`, :func:`cnu_conyuge_vec`,
  :func:`cnu_sobrevivencia_conyuge_vec`: versiones vectoriales (``cnu_afil``, ...).
* :func:`proyectar_cnu`, :func:`proyectar_pension`: proyecciones (``cnu_proy_pensi``).
* :func:`faj_afiliado`, :func:`faj_afiliado_vec`, :func:`calcular_faj`:
  Factor de Ajuste (``cnu_faji``, ``cnu_faj``).
"""

__version__ = "0.1.0"

from .core import (  # noqa: E402
    AGNO_VECTOR,
    EDAD_MAXIMA,
    EDAD_MINIMA,
    TABLA_AFILIADO,
    TABLA_BENEFICIARIO,
    cnu_afiliado,
    cnu_conyuge,
    cnu_sobrevivencia_conyuge,
    describir,
    tasas_por_periodo,
)
from .faj import calcular_faj, faj_afiliado, faj_afiliado_vec, faj_funcion_objetivo  # noqa: E402
from .proyeccion import ProyeccionPension, proyectar_cnu, proyectar_pension  # noqa: E402
from .tablas import (  # noqa: E402
    TablaMortalidad,
    agno_tabla_por_siniestro,
    cargar_tabla_mortalidad,
    cargar_vector_tasas,
    escribir_matriz_mata,
    guardar_tabla_mortalidad,
    guardar_vector_tasas,
    leer_matriz_mata,
    tablas_disponibles,
    vectores_disponibles,
)
from .vectorial import (  # noqa: E402
    AdvertenciaCNU,
    cnu_afiliado_vec,
    cnu_conyuge_vec,
    cnu_sobrevivencia_conyuge_vec,
)


def main() -> None:
    """Punto de entrada del comando ``cnu``."""
    import sys

    from .cli import main as _main

    sys.exit(_main())


__all__ = [
    "AGNO_VECTOR", "EDAD_MAXIMA", "EDAD_MINIMA", "TABLA_AFILIADO", "TABLA_BENEFICIARIO",
    "AdvertenciaCNU", "ProyeccionPension", "TablaMortalidad",
    "agno_tabla_por_siniestro", "calcular_faj", "cargar_tabla_mortalidad", "cargar_vector_tasas",
    "cnu_afiliado", "cnu_afiliado_vec", "cnu_conyuge", "cnu_conyuge_vec",
    "cnu_sobrevivencia_conyuge", "cnu_sobrevivencia_conyuge_vec", "describir",
    "escribir_matriz_mata", "faj_afiliado", "faj_afiliado_vec", "faj_funcion_objetivo",
    "guardar_tabla_mortalidad", "guardar_vector_tasas", "leer_matriz_mata", "main",
    "proyectar_cnu", "proyectar_pension", "tablas_disponibles", "tasas_por_periodo",
    "vectores_disponibles",
]

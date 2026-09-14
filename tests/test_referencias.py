"""Valores de referencia documentados en la ayuda de Stata (cnu.sthlp).

Los ejemplos de ``cnu_afili`` en la ayuda fueron generados con una version
anterior del modulo (se nota en el formato de la etiqueta), y difieren de la
implementacion Mata final en hasta 5e-6; los valores de ``cnu_cnyg_s_hi`` y
``cnu_faji`` coinciden exactamente a 6 decimales.
"""

import numpy as np
import pytest

import cnu


@pytest.mark.parametrize(
    "kwargs, esperado",
    [
        # . cnu_afili 65                     (vector 2013 en el año 2013)
        (dict(x=65, agno_vector=2013, agno_actual=2013), 13.016880),  # obtenido: 13.016877
        # . cnu_afili 65, rp(.0366)          (tasa 3.66% en el año 2014)
        (dict(x=65, rp=0.0366, agno_actual=2014), 13.377540),  # obtenido: 13.377535
        # . cnu_afili 65, agnoa(2011) agnov(2011)
        (dict(x=65, agno_vector=2011, agno_actual=2011), 12.862230),  # obtenido: 12.862231
    ],
)
def test_cnu_afiliado(kwargs, esperado):
    assert cnu.cnu_afiliado(**kwargs) == pytest.approx(esperado, abs=1e-5)


def test_cnu_afiliado_valores_exactos_implementacion():
    """Valores de la implementacion actual, para detectar regresiones."""
    assert cnu.cnu_afiliado(65, agno_vector=2013, agno_actual=2013) == 13.016877
    assert cnu.cnu_afiliado(65, rp=0.0366, agno_actual=2014) == 13.377535
    assert cnu.cnu_afiliado(65, agno_vector=2011, agno_actual=2011) == 12.862231


def test_cnu_conyuge():
    # . cnu_cnyg_s_hi 65 63, agnoa(2011) agnov(2011)   (conymujer=1 por defecto)
    assert cnu.cnu_conyuge(65, 63, agno_vector=2011, agno_actual=2011) == pytest.approx(2.231859, abs=1e-6)


def test_faj_soltero():
    # . cnu_faji 65, rp(.03)   (en 2014)
    assert cnu.faj_afiliado(65, rp=0.03, agno_actual=2014) == pytest.approx(0.066178, abs=1e-6)


def test_faj_con_conyuge():
    # . cnu_faji 65 62, agnov(2013) rp(.03)   (en 2014)
    assert cnu.faj_afiliado(65, 62, agno_vector=2013, rp=0.03, agno_actual=2014) == pytest.approx(0.013094, abs=1e-6)


def test_tablas_2020_explicitas_dan_valores_finitos():
    import math

    for v in (
        cnu.cnu_afiliado(65, tabla="cb2020", agno_actual=2024),
        cnu.cnu_afiliado(60, mujer=True, tabla="rv2020", agno_actual=2024),
        cnu.cnu_conyuge(65, 62, tabla="cb2020", tabla_benef="b2020", agno_actual=2024),
        cnu.cnu_conyuge(60, 65, cot_mujer=True, cony_mujer=False, tabla="rv2020", tabla_benef="cb2020", agno_actual=2024),
        cnu.cnu_sobrevivencia_conyuge(62, mujer=True, tabla_benef="b2020", agno_actual=2024),
        cnu.faj_afiliado(65, tabla="cb2020", agno_actual=2024),
    ):
        assert math.isfinite(v) and v > 0
    r = cnu.proyectar_pension(65, 62, saldo=1000.0, tabla="cb2020", tabla_benef="b2020", agno_actual=2024)
    assert np.all(np.isfinite(r.pension)) and np.all(r.pension > 0)


def test_fsiniestro_resuelve_tablas_2020():
    assert cnu.tabla_mortalidad("rv2009", cnu.ROL_AFILIADO, False, 20240101).nombre == "cnu_tabmor_cb2020h"
    assert cnu.tabla_mortalidad("rv2009", cnu.ROL_AFILIADO, True, 20240101).nombre == "cnu_tabmor_rv2020m"
    assert cnu.tabla_mortalidad("b2006", cnu.ROL_BENEFICIARIO, True, 20240101).nombre == "cnu_tabmor_b2020m"
    assert cnu.tabla_mortalidad("b2006", cnu.ROL_BENEFICIARIO, False, 20240101).nombre == "cnu_tabmor_cb2020h"
    # Lo mismo, de punta a punta: fsiniestro equivale a la tabla 2020 explicita.
    assert cnu.cnu_afiliado(65, fsiniestro=20240101, agno_actual=2024) == cnu.cnu_afiliado(65, tabla="cb2020", agno_actual=2024)
    assert cnu.cnu_afiliado(65, mujer=True, fsiniestro=20240101, agno_actual=2024) == cnu.cnu_afiliado(
        65, mujer=True, tabla="rv2020", agno_actual=2024
    )
    assert cnu.cnu_conyuge(65, 62, fsiniestro=20240101, agno_actual=2024) == cnu.cnu_conyuge(
        65, 62, tabla="cb2020", tabla_benef="b2020", agno_actual=2024
    )
    assert cnu.cnu_conyuge(65, 62, cony_mujer=False, fsiniestro=20240101, agno_actual=2024) == cnu.cnu_conyuge(
        65, 62, cony_mujer=False, tabla="cb2020", tabla_benef="cb2020", agno_actual=2024
    )


def test_fsiniestro_anterior_a_2016_no_cambia():
    # Vigencia 2010-2016: rv2009 / b2006, los mismos defaults historicos.
    assert cnu.cnu_afiliado(65, fsiniestro=20130101, agno_actual=2013) == pytest.approx(13.016877)
    assert cnu.cnu_conyuge(65, 63, fsiniestro=20110301, agno_actual=2011, agno_vector=2011) == pytest.approx(2.231859)
    # Vigencia 2005-2008: rv2004 (mismo valor que pedirla explicitamente).
    assert cnu.cnu_afiliado(65, fsiniestro=20060101, agno_actual=2013) == cnu.cnu_afiliado(65, tabla="rv2004", agno_actual=2013)


def test_describir_muestra_tabla_resuelta():
    d = cnu.describir("soltero sin hijos", "rv2009", agno_actual=2024, fsiniestro=20240101)
    assert "tabla cb2020h" in d
    d = cnu.describir("soltero sin hijos", "rv2009", agno_actual=2024, fsiniestro=20240101, mujer=True)
    assert "tabla rv2020m" in d
    d = cnu.describir("conyuge sin hijos", "rv2009", "b2006", agno_actual=2013, fsiniestro=20130101)
    assert "tablas rv2009h b2006m" in d

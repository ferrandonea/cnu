"""Regla unica de tasa: rv, rp, agno_vector explicito o vector del siniestro anterior a 2014."""

import pytest

import cnu


def test_sin_vector_por_defecto():
    assert cnu.AGNO_VECTOR is None
    assert cnu.INICIO_TITRP == 20140101


@pytest.mark.parametrize("kw", [dict(agno_actual=2026), dict(fsiniestro=20140101), dict()])
def test_sin_tasa_desde_2014_es_error(kw):
    with pytest.raises(ValueError, match=r"TITRP.*rp"):
        cnu.cnu_afiliado(65, **kw)
    with pytest.raises(ValueError, match=r"TITRP.*rp"):
        cnu.cnu_conyuge(65, 63, **kw)
    with pytest.raises(ValueError, match=r"TITRP.*rp"):
        cnu.cnu_sobrevivencia_conyuge(63, **kw)
    with pytest.raises(ValueError, match=r"TITRP.*rp"):
        cnu.describir("soltero sin hijos", "vigente", **kw)


def test_siniestro_anterior_a_2014_usa_el_vector_de_su_agno():
    assert cnu.agno_vector_efectivo(fsiniestro=20131231) == 2013
    assert cnu.cnu_afiliado(65, fsiniestro=20131231) == cnu.cnu_afiliado(65, agno_vector=2013, fsiniestro=20131231)
    assert "vector 2013" in cnu.describir("soltero sin hijos", "vigente", fsiniestro=20131231, agno_actual=2013)
    with pytest.raises(FileNotFoundError, match="2008"):
        cnu.cnu_afiliado(65, fsiniestro=20081231)
    with pytest.raises(FileNotFoundError, match="2008"):
        cnu.tasas_por_periodo(fsiniestro=20081231)


def test_tasa_explicita():
    assert cnu.cnu_afiliado(65, rp=0.0345, agno_actual=2026) == 14.755007
    assert "tasa 3.45%" in cnu.describir("soltero sin hijos", "vigente", rp=0.0345, agno_actual=2026)
    assert "tasa 3.2%" in cnu.describir("soltero sin hijos", "vigente", rv=0.032, agno_actual=2026)


def test_agno_vector_explicito_tiene_prioridad_sobre_fsiniestro():
    assert cnu.agno_vector_efectivo(2013, fsiniestro=20120601) == 2013
    assert cnu.agno_vector_efectivo(2013, fsiniestro=20250101) == 2013
    assert cnu.cnu_afiliado(65, agno_vector=2013, fsiniestro=20120601, agno_actual=2013) == 13.016877
    with pytest.raises(FileNotFoundError):
        cnu.cnu_afiliado(65, agno_vector=1999, fsiniestro=20130101)


def test_no_estricto_devuelve_none_sin_tasa():
    assert cnu.tasas_por_periodo(estricto=False) is None
    assert cnu.tasas_por_periodo(fsiniestro=20081231, estricto=False) is None
    assert cnu.tasas_por_periodo(fsiniestro=20131231, estricto=False) is not None
    assert cnu.tasas_por_periodo(rp=0.03, estricto=False) is not None

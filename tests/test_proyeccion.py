import warnings

import numpy as np
import pytest

import cnu


def test_proyectar_cnu():
    c = cnu.proyectar_cnu(65, agno_actual=2014, rp=0.03)
    assert c.shape == (46,)
    assert c[0] == pytest.approx(cnu.cnu_afiliado(65, rp=0.03, agno_actual=2014))
    # La tabla se fija al inicio de la proyeccion (vigente en 2014: rv2009) y se
    # usa en toda la trayectoria, aunque en 2019 la vigente ya sea otra.
    assert c[5] == pytest.approx(cnu.cnu_afiliado(70, rp=0.03, agno_actual=2019, tabla="rv2009"))
    assert np.all(np.diff(c) < 0)  # el CNU decrece con la edad


def test_proyectar_cnu_con_conyuge():
    c = cnu.proyectar_cnu(65, 62, agno_actual=2014, rp=0.03)
    esperado = cnu.cnu_afiliado(65, rp=0.03, agno_actual=2014) + cnu.cnu_conyuge(65, 62, rp=0.03, agno_actual=2014)
    assert c[0] == pytest.approx(esperado)
    # Cuando el conyuge pasa los 110 su aporte es 0.
    c2 = cnu.proyectar_cnu(65, 100, agno_actual=2014, rp=0.03)
    assert c2[11] == pytest.approx(cnu.cnu_afiliado(76, rp=0.03, agno_actual=2025, tabla="rv2009"))


def test_proyectar_pension_sin_faj():
    r = cnu.proyectar_pension(65, saldo=1000.0, rp=0.03, agno_actual=2014)
    assert not r.con_faj
    assert r.edad[0] == 65 and r.edad[-1] == 110
    cnu0 = cnu.cnu_afiliado(65, rp=0.03, agno_actual=2014)
    assert r.pension[0] == pytest.approx(1000.0 / cnu0)
    assert r.saldo[0] == pytest.approx((1000.0 - r.pension[0]) * 1.03)
    assert np.all(r.saldo >= 0)
    assert r.como_matriz().shape == (46, 3)
    assert list(r.columnas()) == ["edad", "saldo", "pension"]


def test_proyectar_pension_con_faj():
    r = cnu.proyectar_pension(65, faj=True, rp=0.03, agno_actual=2014)
    assert r.con_faj
    assert 0 < r.faj < 1
    assert r.como_matriz().shape == (46, 5)
    assert np.all(r.saldo_faj >= 0)
    sin = cnu.proyectar_pension(65, rp=0.03, agno_actual=2014)
    # La primera pension con FAJ es menor (se reserva una fraccion).
    assert r.pension[0] == pytest.approx(sin.pension[0] * (1 - r.faj))
    # El FAJ garantiza al menos pcent de la primera pension hasta la edad maxima.
    assert np.all(r.pension[: 98 - 65 + 1] >= 0.3 * sin.pension[0] * (1 - 1e-9))


def test_faj_vec_coincide_con_rp_constante():
    v = cnu.faj_afiliado_vec([65], rp=0.03, agno_actual=2014)
    # Con rp constante, cnu_faj_vec usa la misma tasa en la trayectoria del CNU.
    c = cnu.proyectar_cnu(65, rp=0.03, agno_actual=2014)
    e = cnu.calcular_faj(65, c, np.full(110, 0.03), criter=1e-6)
    assert v[0] == pytest.approx(e)
    assert 0 < v[0] < 1


def test_faj_funcion_objetivo_se_anula_en_el_optimo():
    c = cnu.proyectar_cnu(65, rp=0.03, agno_actual=2014)
    rp_a = np.full(110, 0.03)
    f = cnu.calcular_faj(65, c, rp_a, criter=1e-6)
    # En el optimo, la reserva acumulada cubre exactamente el deficit.
    assert cnu.faj_funcion_objetivo(f, 65, c, rp_a) == pytest.approx(0.0, abs=1e-6)
    # Sin retencion (faj = 0) hay deficit; reteniendo todo (faj = 1) hay exceso.
    assert cnu.faj_funcion_objetivo(0.0, 65, c, rp_a) < 0
    assert cnu.faj_funcion_objetivo(1.0, 65, c, rp_a) > 0


def test_proyeccion_sin_tasa_es_error():
    with pytest.raises(ValueError, match=r"TITRP.*rp"):
        cnu.proyectar_pension(65, agno_actual=2026)
    with pytest.raises(ValueError, match=r"TITRP.*rp"):
        cnu.proyectar_cnu(65, agno_actual=2026)
    with pytest.raises(ValueError, match=r"TITRP.*rp"):
        cnu.faj_afiliado(65, agno_actual=2026)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        r = cnu.proyectar_pension(65, rp=0.0345, agno_actual=2026)
    assert r.pension.shape == (46,) and not np.isnan(r.pension).any()
    assert "tasa 3.45%" in r.descripcion


def test_faj_historico_con_vector_explicito():
    assert cnu.faj_afiliado(65, rp=0.03, agno_actual=2014, agno_vector=2013) == pytest.approx(0.066178, abs=1e-6)
    assert cnu.faj_afiliado(65, 62, rp=0.03, agno_actual=2014, agno_vector=2013) == pytest.approx(0.013094, abs=1e-6)


def test_faj_sin_vector_usa_tasa_constante_y_coincide_con_vec():
    f = cnu.faj_afiliado(65, rp=0.03, agno_actual=2014)
    v = cnu.faj_afiliado_vec([65], rp=0.03, agno_actual=2014)
    assert f == pytest.approx(v[0])
    c = cnu.proyectar_cnu(65, rp=0.03, agno_actual=2014)
    assert f == pytest.approx(cnu.calcular_faj(65, c, np.full(110, 0.03), criter=1e-6))
    # Con el vector explicito la trayectoria cambia y el FAJ tambien.
    assert f != pytest.approx(cnu.faj_afiliado(65, rp=0.03, agno_actual=2014, agno_vector=2013))


def test_proyeccion_siniestro_anterior_a_2014_usa_su_vector():
    c = cnu.proyectar_cnu(65, fsiniestro=20131231, agno_actual=2013)
    e = cnu.proyectar_cnu(65, fsiniestro=20131231, agno_actual=2013, agno_vector=2013)
    np.testing.assert_allclose(c, e)
    r = cnu.proyectar_pension(65, fsiniestro=20131231, agno_actual=2013)
    assert "vector 2013" in r.descripcion
    assert not np.isnan(r.pension).any()


def test_faj_vec_sin_tasa_da_nan_y_advierte():
    with pytest.warns(cnu.AdvertenciaCNU, match=r"sin tasa: desde 2014 se requiere rp.*\(1\): 1"):
        v = cnu.faj_afiliado_vec([65, 65], rp=[0.03, np.nan], agno_actual=2014)
    assert not np.isnan(v[0]) and np.isnan(v[1])
    with pytest.warns(cnu.AdvertenciaCNU, match="vector inexistente"):
        v = cnu.faj_afiliado_vec([65], agno_vector=1999, agno_actual=2014)
    assert np.isnan(v[0])

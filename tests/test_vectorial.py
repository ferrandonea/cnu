import numpy as np
import pytest

import cnu


def test_vectorial_coincide_con_escalar():
    edades = np.array([50, 65, 80])
    v = cnu.cnu_afiliado_vec(edades, agno_vector=2013, agno_actual=2013)
    e = [cnu.cnu_afiliado(x, agno_vector=2013, agno_actual=2013) for x in edades]
    np.testing.assert_allclose(v, e)


def test_argumentos_por_fila():
    v = cnu.cnu_afiliado_vec([65, 65, 65], mujer=[False, True, False], rp=[0.0366, 0.0366, np.nan],
                             agno_vector=2013, agno_actual=2014)
    assert v[0] == pytest.approx(13.377540)
    assert v[1] == pytest.approx(cnu.cnu_afiliado(65, mujer=True, rp=0.0366, agno_actual=2014))
    assert v[2] == pytest.approx(cnu.cnu_afiliado(65, agno_vector=2013, agno_actual=2014))


def test_filas_invalidas_dan_nan_y_advierten():
    with pytest.warns(cnu.AdvertenciaCNU, match="menos de 20"):
        v = cnu.cnu_afiliado_vec([19, 65, 111, 70], agno_actual=2013, incluir=[True, True, True, False])
    assert np.isnan(v[0]) and np.isnan(v[2]) and np.isnan(v[3])
    assert not np.isnan(v[1])


def test_vector_inexistente():
    with pytest.warns(cnu.AdvertenciaCNU, match="vector inexistente"):
        v = cnu.cnu_afiliado_vec([65], agno_vector=1999, agno_actual=2013)
    assert np.isnan(v[0])
    # Con tasa unica el vector no se necesita.
    v = cnu.cnu_afiliado_vec([65], agno_vector=1999, rp=0.03, agno_actual=2013)
    assert not np.isnan(v[0])


def test_conyuge_vec():
    v = cnu.cnu_conyuge_vec([65], [63], cony_mujer=True, agno_vector=2011, agno_actual=2011)
    assert v[0] == pytest.approx(2.231859)
    with pytest.warns(cnu.AdvertenciaCNU, match="cónyuges tienen más de 110"):
        v = cnu.cnu_conyuge_vec([65, 65], [63, 111], agno_actual=2011)
    assert np.isnan(v[1])


def test_sobrevivencia_vec():
    v = cnu.cnu_sobrevivencia_conyuge_vec([65, 70], mujer=False, agno_vector=2013, agno_actual=2013)
    e = [cnu.cnu_sobrevivencia_conyuge(y, agno_vector=2013, agno_actual=2013) for y in (65, 70)]
    np.testing.assert_allclose(v, e)


def test_sobrevivencia_es_positiva_y_menor_que_afiliado():
    s = cnu.cnu_sobrevivencia_conyuge(65, agno_actual=2013)
    a = cnu.cnu_afiliado(65, agno_actual=2013)
    assert 0 < s < a

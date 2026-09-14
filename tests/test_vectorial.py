import numpy as np
import pytest

import cnu


def test_vectorial_coincide_con_escalar():
    edades = np.array([50, 65, 80])
    v = cnu.cnu_afiliado_vec(edades, agno_vector=2013, agno_actual=2013)
    e = [cnu.cnu_afiliado(x, agno_vector=2013, agno_actual=2013) for x in edades]
    np.testing.assert_allclose(v, e)
    # La tasa de cada fila se resuelve como en la escalar equivalente.
    fechas = [20120601, 20250101, 20130101]
    rp = [np.nan, 0.03, np.nan]
    v = cnu.cnu_afiliado_vec(edades, fsiniestro=fechas, rp=rp, agno_actual=2025)
    e = [cnu.cnu_afiliado(x, fsiniestro=f, rp=r if not np.isnan(r) else None, agno_actual=2025)
         for x, f, r in zip(edades, fechas, rp)]
    np.testing.assert_allclose(v, e)


def test_argumentos_por_fila():
    v = cnu.cnu_afiliado_vec([65, 65, 65], mujer=[False, True, False], rp=[0.0366, 0.0366, np.nan],
                             agno_vector=2013, agno_actual=2014)
    assert v[0] == pytest.approx(13.377540)
    assert v[1] == pytest.approx(cnu.cnu_afiliado(65, mujer=True, rp=0.0366, agno_actual=2014))
    assert v[2] == pytest.approx(cnu.cnu_afiliado(65, agno_vector=2013, agno_actual=2014))


def test_filas_invalidas_dan_nan_y_advierten():
    with pytest.warns(cnu.AdvertenciaCNU, match="menos de 20"):
        v = cnu.cnu_afiliado_vec([19, 65, 111, 70], agno_vector=2013, agno_actual=2013, incluir=[True, True, True, False])
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
        v = cnu.cnu_conyuge_vec([65, 65], [63, 111], agno_vector=2011, agno_actual=2011)
    assert np.isnan(v[1])


def test_sobrevivencia_vec():
    v = cnu.cnu_sobrevivencia_conyuge_vec([65, 70], mujer=False, agno_vector=2013, agno_actual=2013)
    e = [cnu.cnu_sobrevivencia_conyuge(y, agno_vector=2013, agno_actual=2013) for y in (65, 70)]
    np.testing.assert_allclose(v, e)


def test_sobrevivencia_es_positiva_y_menor_que_afiliado():
    s = cnu.cnu_sobrevivencia_conyuge(65, agno_vector=2013, agno_actual=2013)
    a = cnu.cnu_afiliado(65, agno_vector=2013, agno_actual=2013)
    assert 0 < s < a


def test_fsiniestro_por_fila():
    fechas = [20040101, 20130101, 20200101, 20240101]
    v = cnu.cnu_afiliado_vec([65, 65, 65, 65], fsiniestro=fechas, rp=0.03, agno_actual=2024)
    esperado = [cnu.cnu_afiliado(65, tabla=t, rp=0.03, agno_actual=2024) for t in ("rv1985", "rv2009", "cb2014", "cb2020")]
    np.testing.assert_allclose(v, esperado)
    assert len(set(v)) == 4


def test_regla_de_tasa_fila_a_fila():
    fechas = [20120601, 20250101, 20250101]
    with pytest.warns(cnu.AdvertenciaCNU, match=r"sin tasa: desde 2014 se requiere rp.*\(1\): 2") as w:
        v = cnu.cnu_afiliado_vec([65, 65, 65], fsiniestro=fechas, rp=[np.nan, 0.03, np.nan], agno_actual=2025)
    assert len(w) == 1
    assert v[0] == pytest.approx(cnu.cnu_afiliado(65, fsiniestro=20120601, agno_actual=2025))
    assert v[1] == pytest.approx(cnu.cnu_afiliado(65, fsiniestro=20250101, rp=0.03, agno_actual=2025))
    assert np.isnan(v[2])


def test_sin_tasa_ni_fecha_por_fila():
    with pytest.warns(cnu.AdvertenciaCNU, match=r"sin tasa.*\(1\): 1"):
        v = cnu.cnu_afiliado_vec([65, 65], rp=[0.03, np.nan], agno_actual=2025)
    assert v[0] == pytest.approx(cnu.cnu_afiliado(65, rp=0.03, agno_actual=2025))
    assert np.isnan(v[1])
    with pytest.warns(cnu.AdvertenciaCNU, match="sin tasa"):
        v = cnu.cnu_conyuge_vec([65, 65], [63, 63], rp=[np.nan, 0.03], agno_actual=2025)
    assert np.isnan(v[0]) and not np.isnan(v[1])
    with pytest.warns(cnu.AdvertenciaCNU, match="sin tasa"):
        v = cnu.cnu_sobrevivencia_conyuge_vec([63, 63], rv=[0.03, np.nan], agno_actual=2025)
    assert not np.isnan(v[0]) and np.isnan(v[1])


def test_sin_tasa_y_vector_inexistente_se_distinguen():
    with pytest.warns(cnu.AdvertenciaCNU) as w:
        v = cnu.cnu_afiliado_vec([65, 65, 65], fsiniestro=[20250101, 20081231, 20130101], agno_actual=2025)
    assert len(w) == 1
    msg = str(w[0].message)
    assert "(1) Las siguientes observaciones quedan sin tasa" in msg and "(1): 0\n" in msg
    assert "(2) Para las siguientes observaciones se intentó utilizar un vector inexistente (1): 1" in msg
    assert np.isnan(v[0]) and np.isnan(v[1]) and not np.isnan(v[2])


def test_hijo_vec_coincide_con_escalar():
    x, h, mujer = [65, 60, 65], [10, 21, 30], [False, True, False]
    v = cnu.cnu_hijo_vec(x, h, cot_mujer=[False, True, False], hijo_mujer=mujer, rp=0.03, agno_actual=2026)
    e = [cnu.cnu_hijo(a, b, c, m, rp=0.03, agno_actual=2026) for a, b, c, m in zip(x, h, [False, True, False], mujer)]
    np.testing.assert_allclose(v, e)
    assert v[2] == 0.0
    v = cnu.cnu_sobrevivencia_hijo_vec(h, mujer=mujer, rp=[0.03, np.nan, 0.03], fsiniestro=[0, 20130101, 0], agno_actual=2026)
    e = [cnu.cnu_sobrevivencia_hijo(10, rp=0.03, agno_actual=2026),
         cnu.cnu_sobrevivencia_hijo(21, mujer=True, fsiniestro=20130101, agno_actual=2026), 0.0]
    np.testing.assert_allclose(v, e)


def test_hijo_vec_filas_invalidas():
    with pytest.warns(cnu.AdvertenciaCNU, match="hijos tienen edad negativa") as w:
        v = cnu.cnu_hijo_vec([65, 19, 65, 65], [-1, 10, 10, 10], rp=[0.03, 0.03, np.nan, 0.03],
                             agno_actual=2026, incluir=[True, True, True, False])
    assert "cotizantes tienen menos de 20" in str(w[0].message) and "sin tasa" in str(w[0].message)
    assert np.isnan(v).all()
    with pytest.warns(cnu.AdvertenciaCNU, match="edad negativa"):
        v = cnu.cnu_sobrevivencia_hijo_vec([-1, 0, np.nan], rp=0.03, agno_actual=2026)
    assert np.isnan(v[0]) and v[1] > 0 and np.isnan(v[2])


def test_hijo_invalido_vec_coincide_con_escalar():
    x, h, mujer, parcial = [65, 60, 65, 65], [10, 21, 30, 30], [False, True, False, True], [False, True, False, True]
    cot = [False, True, False, False]
    v = cnu.cnu_hijo_invalido_vec(x, h, cot_mujer=cot, hijo_mujer=mujer, parcial=parcial, rp=0.03, agno_actual=2026)
    e = [cnu.cnu_hijo_invalido(a, b, c, m, p, rp=0.03, agno_actual=2026) for a, b, c, m, p in zip(x, h, cot, mujer, parcial)]
    np.testing.assert_allclose(v, e)
    assert (v > 0).all()  # sin edad limite: los hijos de 30 tienen CNU positivo
    v = cnu.cnu_sobrevivencia_hijo_invalido_vec(h, mujer=mujer, parcial=True, rp=[0.03, np.nan, 0.03, 0.03],
                                                fsiniestro=[0, 20130101, 0, 0], agno_actual=2026)
    e = [cnu.cnu_sobrevivencia_hijo_invalido(10, parcial=True, rp=0.03, agno_actual=2026),
         cnu.cnu_sobrevivencia_hijo_invalido(21, mujer=True, parcial=True, fsiniestro=20130101, agno_actual=2026),
         cnu.cnu_sobrevivencia_hijo_invalido(30, parcial=True, rp=0.03, agno_actual=2026),
         cnu.cnu_sobrevivencia_hijo_invalido(30, mujer=True, parcial=True, rp=0.03, agno_actual=2026)]
    np.testing.assert_allclose(v, e)


def test_hijo_invalido_vec_filas_invalidas():
    with pytest.warns(cnu.AdvertenciaCNU, match="hijos tienen edad negativa") as w:
        v = cnu.cnu_hijo_invalido_vec([65, 19, 65, 65], [-1, 10, 10, 10], rp=[0.03, 0.03, np.nan, 0.03],
                                      agno_actual=2026, incluir=[True, True, True, False])
    assert "cotizantes tienen menos de 20" in str(w[0].message) and "sin tasa" in str(w[0].message)
    assert np.isnan(v).all()
    with pytest.warns(cnu.AdvertenciaCNU, match="edad negativa"):
        v = cnu.cnu_sobrevivencia_hijo_invalido_vec([-1, 0, np.nan], parcial=[True, False, True], rp=0.03, agno_actual=2026)
    assert np.isnan(v[0]) and v[1] > 0 and np.isnan(v[2])


def test_conyuge_con_hijos_vec_coincide_con_escalar():
    x, y, h = [65, 60, 65, 65], [63, 62, 63, 63], [10, 21, 30, 5]
    cot, cony, inv = [False, True, False, False], [True, False, True, True], [False, False, False, True]
    v = cnu.cnu_conyuge_con_hijos_vec(x, y, h, cot_mujer=cot, cony_mujer=cony, hijo_invalido=inv, rp=0.03, agno_actual=2026)
    e = [cnu.cnu_conyuge_con_hijos(a, b, c, d, f, g, rp=0.03, agno_actual=2026)
         for a, b, c, d, f, g in zip(x, y, h, cot, cony, inv)]
    np.testing.assert_allclose(v, e)
    assert v[2] == cnu.cnu_conyuge(65, 63, rp=0.03, agno_actual=2026)  # hijo de 30: como sin hijos
    v = cnu.cnu_sobrevivencia_conyuge_con_hijos_vec(y, h, mujer=cony, hijo_invalido=inv, rp=[0.03, np.nan, 0.03, 0.03],
                                                    fsiniestro=[0, 20130101, 0, 0], agno_actual=2026)
    e = [cnu.cnu_sobrevivencia_conyuge_con_hijos(63, 10, mujer=True, rp=0.03, agno_actual=2026),
         cnu.cnu_sobrevivencia_conyuge_con_hijos(62, 21, fsiniestro=20130101, agno_actual=2026),
         cnu.cnu_sobrevivencia_conyuge(63, mujer=True, rp=0.03, agno_actual=2026),
         cnu.cnu_sobrevivencia_conyuge_con_hijos(63, 5, mujer=True, hijo_invalido=True, rp=0.03, agno_actual=2026)]
    np.testing.assert_allclose(v, e)


def test_conyuge_con_hijos_vec_filas_invalidas():
    with pytest.warns(cnu.AdvertenciaCNU, match="hijos tienen edad negativa") as w:
        v = cnu.cnu_conyuge_con_hijos_vec([65, 19, 65, 65, 65, 65], [63, 63, 19, 111, 63, 63], [-1, 10, 10, 10, 10, 10],
                                          rp=[0.03, 0.03, 0.03, 0.03, np.nan, 0.03], agno_actual=2026,
                                          incluir=[True, True, True, True, True, False])
    msg = str(w[0].message)
    assert "cotizantes tienen menos de 20" in msg and "cónyuges tienen menos de 20" in msg
    assert "cónyuges tienen más de 110" in msg and "sin tasa" in msg
    assert np.isnan(v).all()
    with pytest.warns(cnu.AdvertenciaCNU, match="edad negativa"):
        v = cnu.cnu_sobrevivencia_conyuge_con_hijos_vec([63, 63, 63, 19], [-1, 0, np.nan, 10], rp=0.03, agno_actual=2026)
    assert np.isnan(v[0]) and v[1] > 0 and np.isnan(v[2]) and np.isnan(v[3])

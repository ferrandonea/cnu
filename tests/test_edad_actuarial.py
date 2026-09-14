"""Edad actuarial: redondeo al entero mas cercano con el medio hacia arriba."""

import datetime

import numpy as np
import pytest

import cnu
from cnu.cli import main


def test_edad_actuarial_desde_fechas():
    assert cnu.edad_actuarial(19600315, 20260314) == 66
    assert cnu.edad_actuarial(19600915, 20260315) == 66
    assert cnu.edad_actuarial(19600916, 20260315) == 65
    assert cnu.edad_actuarial(datetime.date(1960, 9, 15), datetime.date(2026, 3, 15)) == 66
    assert cnu.edad_actuarial(datetime.date(1960, 9, 16), datetime.date(2026, 3, 15)) == 65
    assert cnu.edad_actuarial(19600315, 20260315) == 66  # cumpleagnos exacto
    assert cnu.edad_actuarial(19600229, 20260228) == 66  # nacido un 29 de febrero
    with pytest.raises(ValueError):
        cnu.edad_actuarial(20260315, 19600315)


def test_edad_entera_redondea_medio_hacia_arriba():
    assert cnu.edad_entera(65.4) == 65 and cnu.edad_entera(65.5) == 66 and cnu.edad_entera(65.7) == 66
    assert cnu.edad_entera(65) == 65 and cnu.edad_entera(np.float64(19.6)) == 20


def test_escalares_redondean():
    kw = dict(rp=0.0345, agno_actual=2026)
    assert cnu.cnu_afiliado(65.7, **kw) == cnu.cnu_afiliado(66, **kw)
    assert cnu.cnu_afiliado(65.4, **kw) == cnu.cnu_afiliado(65, **kw)
    assert cnu.cnu_conyuge(65.7, 62.5, **kw) == cnu.cnu_conyuge(66, 63, **kw)
    assert cnu.cnu_conyuge(65.4, 62.4, **kw) == cnu.cnu_conyuge(65, 62, **kw)
    assert cnu.cnu_sobrevivencia_conyuge(62.5, **kw) == cnu.cnu_sobrevivencia_conyuge(63, **kw)


def test_rango_se_valida_despues_del_redondeo():
    kw = dict(rp=0.0345, agno_actual=2026)
    assert cnu.cnu_afiliado(19.6, **kw) == cnu.cnu_afiliado(20, **kw)
    # El rango [20, 110] se valida en las vectoriales, sobre la edad ya redondeada:
    # 19.4 queda fuera (nan + advertencia) y 19.6 se calcula como 20.
    with pytest.warns(cnu.AdvertenciaCNU, match="menos de 20"):
        v = cnu.cnu_afiliado_vec([19.4, 19.6], **kw)
    assert np.isnan(v[0]) and v[1] == pytest.approx(cnu.cnu_afiliado(20, **kw))


def test_vectoriales_redondean_y_conservan_nan():
    kw = dict(rp=0.0345, agno_actual=2026)
    v = cnu.cnu_afiliado_vec([65.4, 65.6, np.nan], **kw)
    assert v[0] == pytest.approx(cnu.cnu_afiliado(65, **kw))
    assert v[1] == pytest.approx(cnu.cnu_afiliado(66, **kw))
    assert np.isnan(v[2])
    v = cnu.cnu_conyuge_vec([65.6], [62.5], cony_mujer=True, **kw)
    assert v[0] == pytest.approx(cnu.cnu_conyuge(66, 63, **kw))
    v = cnu.cnu_sobrevivencia_conyuge_vec([62.5, np.nan], **kw)
    assert v[0] == pytest.approx(cnu.cnu_sobrevivencia_conyuge(63, **kw)) and np.isnan(v[1])


def test_faj_y_proyeccion_redondean():
    kw = dict(rp=0.03, agno_actual=2014)
    assert cnu.faj_afiliado(65.7, **kw) == pytest.approx(cnu.faj_afiliado(66, **kw))
    assert cnu.faj_afiliado(65.7, 62.5, **kw) == pytest.approx(cnu.faj_afiliado(66, 63, **kw))
    v = cnu.faj_afiliado_vec([65.7, 65.4], y=[62.5, np.nan], cony_mujer=True, **kw)
    assert v[0] == pytest.approx(cnu.faj_afiliado(66, 63, **kw)) and v[1] == pytest.approx(cnu.faj_afiliado(65, **kw))
    a, b = cnu.proyectar_pension(65.7, 62.5, **kw), cnu.proyectar_pension(66, 63, **kw)
    np.testing.assert_allclose(a.pension, b.pension)
    np.testing.assert_allclose(cnu.proyectar_cnu(65.4, **kw), cnu.proyectar_cnu(65, **kw))


def test_cli_acepta_decimales_y_muestra_la_edad(capsys):
    assert main(["afil", "65.7", "--rp", "0.0345", "--agno-actual", "2026"]) == 0
    lineas = capsys.readouterr().out.strip().splitlines()
    assert "66" in lineas[0] and "65.7" in lineas[0]
    assert lineas[-1].strip() == "14.322867"
    assert main(["afil", "65", "--rp", "0.0345", "--agno-actual", "2026"]) == 0
    assert "edad actuarial" not in capsys.readouterr().out.splitlines()[0]
    assert main(["conyuge", "65.7", "62.5", "--rp", "0.0345", "--agno-actual", "2026"]) == 0
    primera = capsys.readouterr().out.splitlines()[0]
    assert "afiliado 65.7 -> 66" in primera and "conyuge 62.5 -> 63" in primera
    assert main(["faj", "65.7", "--rp", "0.03", "--agno-actual", "2014"]) == 0
    assert "-> 66" in capsys.readouterr().out.splitlines()[0]
    assert main(["proy", "65.7", "--rp", "0.03", "--agno-actual", "2014"]) == 0
    assert "-> 66" in capsys.readouterr().out.splitlines()[0]

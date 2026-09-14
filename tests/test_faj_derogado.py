"""FAJ derogado por la Ley 21.419 desde el 1 de febrero de 2022: advertencia, no error."""

import warnings

import numpy as np
import pytest

import cnu
from cnu.cli import main

MATCH = r"21\.419.*1 de febrero de 2022"


def _sin_advertencias(fn):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        return fn()


def test_constante():
    assert cnu.DEROGACION_FAJ == 20220201
    assert cnu.faj_derogado(agno_actual=2026) and not cnu.faj_derogado(agno_actual=2021)
    assert cnu.faj_derogado(20220201) and not cnu.faj_derogado(20220131)


def test_faj_posterior_advierte_y_devuelve_valor():
    with pytest.warns(cnu.AdvertenciaCNU, match=MATCH) as w:
        v = cnu.faj_afiliado(65, rp=0.03, agno_actual=2026)
    assert len(w) == 1 and 0 < v < 1


def test_faj_historico_no_advierte():
    v = _sin_advertencias(lambda: cnu.faj_afiliado(65, rp=0.03, agno_actual=2014, agno_vector=2013))
    assert v == pytest.approx(0.066178, abs=1e-6)


def test_fsiniestro_decide_aunque_agno_actual_sea_2022():
    _sin_advertencias(lambda: cnu.faj_afiliado(65, rp=0.03, fsiniestro=20220131, agno_actual=2022))
    with pytest.warns(cnu.AdvertenciaCNU, match=MATCH):
        cnu.faj_afiliado(65, rp=0.03, fsiniestro=20220201, agno_actual=2022)


def test_faj_vec_una_sola_advertencia():
    with pytest.warns(cnu.AdvertenciaCNU, match=MATCH) as w:
        v = cnu.faj_afiliado_vec([65, 66, 67], rp=0.03, agno_actual=[2026, 2025, 2014])
    assert len(w) == 1 and "2 observaciones" in str(w[0].message)
    assert not np.isnan(v).any()
    v = _sin_advertencias(lambda: cnu.faj_afiliado_vec([65, 66], rp=0.03, agno_actual=2014))
    assert not np.isnan(v).any()


def test_proyeccion_solo_advierte_con_faj():
    r = _sin_advertencias(lambda: cnu.proyectar_pension(65, rp=0.0345, agno_actual=2026))
    assert not r.con_faj
    with pytest.warns(cnu.AdvertenciaCNU, match=MATCH) as w:
        r = cnu.proyectar_pension(65, rp=0.0345, agno_actual=2026, faj=True)
    assert len(w) == 1 and r.con_faj


def test_cli_advierte_en_stderr_con_codigo_0(capsys):
    assert main(["faj", "65", "--rp", "0.03", "--agno-actual", "2026"]) == 0
    out, err = capsys.readouterr()
    assert "advertencia" in err and "21.419" in err and "1 de febrero de 2022" in err
    assert float(out.strip().splitlines()[-1]) > 0
    assert main(["proy", "65", "--faj", "--csv", "--rp", "0.03", "--agno-actual", "2026"]) == 0
    out, err = capsys.readouterr()
    assert "21.419" in err and out.startswith("edad,saldo,faj,saldo_faj,pension")
    assert main(["faj", "65", "--rp", "0.03", "--agno-vector", "2013", "--agno-actual", "2014"]) == 0
    assert capsys.readouterr().err == ""

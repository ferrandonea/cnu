"""Los ejemplos numericos del README se reproducen con el codigo."""

import datetime
import inspect
import warnings

import numpy as np
import pytest

import cnu
from cnu.cli import main


def test_ejemplos_actuales_tm2020():
    assert cnu.cnu_afiliado(65, rp=0.03, agno_actual=2026) == 15.456439
    assert cnu.cnu_afiliado(60, mujer=True, rp=0.03, agno_actual=2026) == 19.764704
    assert cnu.cnu_afiliado(65, agno_vector=2013, agno_actual=2026) == 14.042741
    assert cnu.cnu_conyuge(65, 63, cony_mujer=True, rp=0.03, agno_actual=2026) == 2.493278
    assert cnu.cnu_sobrevivencia_conyuge(63, mujer=True, rp=0.03, agno_actual=2026) == 10.674379
    assert cnu.cnu_hijo(65, 10, rp=0.03, agno_actual=2026) == 0.135662
    assert cnu.cnu_hijo(65, 30, rp=0.03, agno_actual=2026) == 0.0
    assert cnu.cnu_sobrevivencia_hijo(10, mujer=True, rp=0.03, agno_actual=2026) == 1.720195
    assert cnu.cnu_hijo_invalido(65, 30, rp=0.03, agno_actual=2026) == 1.257455
    assert cnu.cnu_hijo_invalido(65, 21, hijo_mujer=True, parcial=True, rp=0.03, agno_actual=2026) == 1.259397
    assert cnu.cnu_sobrevivencia_hijo_invalido(21, mujer=True, rp=0.03, agno_actual=2026) == 3.939510
    assert cnu.cnu_conyuge_con_hijos(65, 63, 10, rp=0.03, agno_actual=2026) == 2.409035
    assert cnu.cnu_conyuge_con_hijos(65, 63, 10, hijo_invalido=True, rp=0.03, agno_actual=2026) == 2.077732
    assert cnu.cnu_sobrevivencia_conyuge_con_hijos(63, 10, mujer=True, rp=0.03, agno_actual=2026) == 9.578224
    assert cnu.cnu_conyuge(65, 63, conviviente=True, rp=0.03, agno_actual=2026) == 2.493278
    assert cnu.cnu_madre_padre(50, 45, 21, rp=0.03, agno_actual=2026) == 1.370247
    assert cnu.cnu_madre_padre(50, 45, rp=0.03, agno_actual=2026) == 1.370831
    assert cnu.cnu_sobrevivencia_madre_padre(45, 21, hijo_invalido=True, rp=0.03, agno_actual=2026) == 7.264773
    assert cnu.cnu_padres(65, 88, rp=0.03, agno_actual=2026) == 0.161421
    assert cnu.cnu_padres(65, 88, madre=False, rp=0.03, agno_actual=2026) == 0.115149
    assert cnu.cnu_sobrevivencia_padres(88, rp=0.03, agno_actual=2026) == 3.089039
    assert cnu.faj_afiliado(65, rp=0.03, agno_vector=2013, agno_actual=2026) == pytest.approx(0.037205, abs=1e-6)
    assert cnu.faj_afiliado(65, 62, rp=0.03, agno_vector=2013, agno_actual=2026) == pytest.approx(0.004659, abs=1e-6)
    p = cnu.proyectar_pension(65, saldo=1000, rp=0.03, agno_actual=2026)
    assert p.pension[0] == pytest.approx(64.6979, abs=1e-4)
    with pytest.warns(cnu.AdvertenciaCNU, match="21.419"):
        p = cnu.proyectar_pension(65, saldo=1000, rp=0.03, faj=True, agno_actual=2026)
    assert p.pension[0] == pytest.approx(63.2245, abs=1e-4)
    assert p.faj == pytest.approx(0.022775, abs=1e-6)
    assert cnu.cnu_afiliado(65, fsiniestro=20230630, rp=0.03, agno_actual=2023) == 15.063535
    assert cnu.cnu_afiliado(65, fsiniestro=20230701, rp=0.03, agno_actual=2023) == 15.320124
    assert cnu.describir("soltero sin hijos", "vigente", rp=0.03, agno_actual=2026) == (
        "CNU RP para soltero sin hijos (tabla cb2020h), tasa 3% en el año 2026"
    )


def test_ejemplos_historicos():
    assert cnu.cnu_afiliado(65, agno_vector=2013, agno_actual=2013) == 13.016877
    assert cnu.cnu_afiliado(65, tabla="rv2009", agno_vector=2013, agno_actual=2013) == 13.016877
    assert cnu.cnu_afiliado(65, rp=0.0366, agno_actual=2014) == 13.377535
    assert cnu.cnu_conyuge(65, 63, cony_mujer=True, agno_vector=2011, agno_actual=2011) == pytest.approx(2.231859, abs=1e-6)
    assert cnu.faj_afiliado(65, rp=0.03, agno_vector=2013, agno_actual=2014) == pytest.approx(0.066178, abs=1e-6)
    assert cnu.faj_afiliado(65, 62, rp=0.03, agno_vector=2013, agno_actual=2014) == pytest.approx(0.013094, abs=1e-6)
    assert cnu.tabla_mortalidad("rv2009", cnu.ROL_AFILIADO, False, agno_actual=2026).nombre == "cnu_tabmor_rv2009h"


def test_vectorial_por_fsiniestro():
    v = cnu.cnu_afiliado_vec([55, 65, 75], fsiniestro=[20130101, 20200101, 20240101], rp=0.03, agno_actual=2026)
    esperado = [
        cnu.cnu_afiliado(55, tabla="rv2009", rp=0.03, agno_actual=2026),
        cnu.cnu_afiliado(65, tabla="cb2014", rp=0.03, agno_actual=2026),
        cnu.cnu_afiliado(75, tabla="cb2020", rp=0.03, agno_actual=2026),
    ]
    np.testing.assert_allclose(v, esperado)
    edades = np.array([55, 65, 75])
    v = cnu.cnu_hijo_invalido_vec(edades, [3, 12, 25], parcial=[0, 1, 1], rp=0.03, agno_actual=2026)
    assert (v > 0).all() and v[2] == cnu.cnu_hijo_invalido(75, 25, parcial=True, rp=0.03, agno_actual=2026)
    v = cnu.cnu_conyuge_con_hijos_vec(edades, [53, 63, 73], [3, 12, 25], cony_mujer=True, rp=0.03, agno_actual=2026)
    assert (v > 0).all() and v[2] == cnu.cnu_conyuge(75, 73, rp=0.03, agno_actual=2026)
    v = cnu.cnu_madre_padre_vec(edades, [50, 60, 70], [3, 12, np.nan], rp=0.03, agno_actual=2026)
    assert (v > 0).all() and v[2] == cnu.cnu_madre_padre(75, 70, rp=0.03, agno_actual=2026)
    v = cnu.cnu_padres_vec(edades, [80, 88, 95], madre=[1, 0, 1], rp=0.03, agno_actual=2026)
    assert (v > 0).all() and v[1] == cnu.cnu_padres(65, 88, madre=False, rp=0.03, agno_actual=2026)


def test_selector_y_tabla_bidimensional():
    assert cnu.tabla_por_fecha(20240101, "rv", "h") == ("cb", 2020)
    assert cnu.tabla_por_fecha(20240101, "rv", "m") == ("rv", 2020)
    assert cnu.tabla_por_fecha(20200101, "b", "h") == ("cb", 2014)
    assert cnu.tabla_mortalidad("vigente", cnu.ROL_AFILIADO, mujer=False, agno_actual=2026).nombre == "cnu_tabmor_cb2020h"
    t = cnu.cargar_tabla_mortalidad("cb", 2020, "h")
    assert t.bidimensional and t.agnos_aa[0] == 2021 and t.agnos_aa[-1] == 2036
    assert t.qx[65] == pytest.approx(0.00887369)
    assert t.qx_mejorado(2022, 65)[65] == pytest.approx(0.0085260, abs=5e-8)


def test_tablas_propias_ambos_esquemas(tmp_path):
    d = str(tmp_path)
    t = cnu.cargar_tabla_mortalidad("cb", 2020, "h")
    cnu.guardar_tabla_mortalidad(t, 2020, "h", "cb", d)
    cnu.guardar_tabla_mortalidad(t.como_matriz(), 2020, "h", "cb", d, reemplazar=True, agnos_aa=range(2021, 2037))
    cnu.guardar_tabla_mortalidad(cnu.cargar_tabla_mortalidad("rv", 2009, "h"), 2009, "h", "rv", d, formato="mata")
    assert cnu.cnu_afiliado(65, rp=0.03, agno_actual=2026, dir_tablas=d) == 15.456439
    assert cnu.cnu_afiliado(65, tabla="rv2009", rp=0.03, agno_actual=2026, dir_tablas=d) == cnu.cnu_afiliado(
        65, tabla="rv2009", rp=0.03, agno_actual=2026
    )


def test_cli_ejemplo(capsys):
    assert main(["afil", "65", "--fsiniestro", "20240315", "--rp", "0.03", "--agno-actual", "2026"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "CNU RP para soltero sin hijos (tabla cb2020h), tasa 3% en el año 2026"
    assert out[1].strip() == "15.456439"
    assert main(["hijo", "65", "10", "--rp", "0.03", "--agno-actual", "2026"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "CNU RP para hijo no inválido 15% (tablas cb2020h cb2020h), tasa 3% en el año 2026"
    assert out[1].strip() == "0.135662"
    assert main(["hijo-inv", "65", "30", "--rp", "0.03", "--agno-actual", "2026"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "CNU RP para hijo inválido total 15% (tablas cb2020h mi2020h), tasa 3% en el año 2026"
    assert out[1].strip() == "1.257455"
    assert main(["conyuge-ch", "65", "63", "10", "--rp", "0.03", "--agno-actual", "2026"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "CNU RP para cónyuge con hijos 50%/60% (tablas cb2020h b2020m), tasa 3% en el año 2026"
    assert out[1].strip() == "2.409035"
    assert main(["madre-padre", "50", "45", "21", "--rp", "0.03", "--agno-actual", "2026"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "CNU RP para madre no matrimonial con hijos 30%/36% (tablas cb2020h b2020m), tasa 3% en el año 2026"
    assert out[1].strip() == "1.370247"
    assert main(["padres", "65", "88", "--rp", "0.03", "--agno-actual", "2026"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "CNU RP para madre del afiliado 50% (tablas cb2020h b2020m), tasa 3% en el año 2026"
    assert out[1].strip() == "0.161421"


def test_estado_normativo_y_edad_actuarial():
    assert cnu.cnu_afiliado(65, rp=0.0345, agno_actual=2026) == 14.755007
    assert cnu.edad_actuarial(19600915, 20260315) == 66
    assert cnu.edad_actuarial(datetime.date(1960, 9, 15), datetime.date(2026, 3, 15)) == 66
    assert cnu.cnu_afiliado(65.7, rp=0.0345, agno_actual=2026) == 14.322867
    assert cnu.cnu_afiliado(65.7, rp=0.0345, agno_actual=2026) == cnu.cnu_afiliado(66, rp=0.0345, agno_actual=2026)
    assert cnu.DEROGACION_FAJ == 20220201
    with pytest.warns(cnu.AdvertenciaCNU, match="21.419"):
        assert cnu.faj_afiliado(65, rp=0.03, agno_vector=2013, agno_actual=2026) == pytest.approx(0.037205, abs=1e-6)


def test_ningun_ejemplo_depende_de_una_tasa_por_defecto():
    """Sin tasa, todo falla: los ejemplos del README pasan rp, rv, agno_vector o un siniestro anterior a 2014."""
    for fn in (cnu.cnu_afiliado, cnu.faj_afiliado, cnu.proyectar_cnu):
        with pytest.raises(ValueError, match="TITRP"):
            fn(65, agno_actual=2026)
    with pytest.raises(ValueError, match="TITRP"):
        cnu.proyectar_pension(65, agno_actual=2026)
    with pytest.raises(ValueError, match="TITRP"):
        cnu.cnu_conyuge(65, 63, agno_actual=2026)
    with pytest.warns(cnu.AdvertenciaCNU, match="sin tasa"):
        assert np.isnan(cnu.cnu_afiliado_vec([65], agno_actual=2026)).all()


def test_defaults_publicos_sin_2013_ni_0_03():
    publicas = [getattr(cnu, n) for n in cnu.__all__ if callable(getattr(cnu, n)) and not isinstance(getattr(cnu, n), type)]
    for fn in publicas:
        for nombre, p in inspect.signature(fn).parameters.items():
            if nombre in ("rp", "rv", "agno_vector"):
                assert p.default in (None, inspect.Parameter.empty), (fn.__name__, nombre, p.default)
            assert p.default not in (2013, 0.03), (fn.__name__, nombre)
    assert cnu.AGNO_VECTOR is None


def test_version_cli(capsys):
    with pytest.raises(SystemExit) as e:
        main(["--version"])
    assert e.value.code == 0
    assert capsys.readouterr().out.strip() == f"cnu {cnu.__version__}" == "cnu 0.3.0"

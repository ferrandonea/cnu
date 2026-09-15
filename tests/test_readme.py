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
    g = cnu.cnu_grupo_familiar(cnu.Afiliado(65), [cnu.Beneficiario("conyuge", 63), cnu.Beneficiario("hijo", 10)],
                               rp=0.03, agno_actual=2026)
    assert g.total == 18.001136
    assert [c.cnu for c in g.componentes] == [15.456439, 2.409035, 0.135662]
    assert [c.etiqueta for c in g.componentes] == ["afiliado", "cónyuge con hijos 50%/60%", "hijo no inválido 15%"]
    assert g.componentes[1].porcentajes == (0.5, 0.6)
    assert g.descripcion == ("CNU RP para grupo familiar: afiliado, cónyuge con hijos 50%/60%, hijo no inválido 15% "
                             "(tablas cb2020h b2020m), tasa 3% en el año 2026")
    assert cnu.cnu_grupo_familiar(cnu.Afiliado(65), [("conyuge", 63), ("hijo", 10), ("hijo_invalido", 20)],
                                  rp=0.03, agno_actual=2026).componentes[1].etiqueta == "cónyuge con hijo inválido 50%"
    assert cnu.cnu_grupo_familiar(None, [("conyuge", 63), ("hijo", 10, True)], rp=0.03, agno_actual=2026).total == 11.298419
    assert cnu.cnu_grupo_familiar(cnu.Afiliado(65), [("conyuge", 63), ("hijo", 10)], valor_uf=1,
                                  rp=0.03, agno_actual=2026).total == 33.001136
    assert cnu.CUOTA_MORTUORIA_UF == 15
    with pytest.raises(cnu.ErrorGrupoFamiliar, match="articulo 58"):
        cnu.cnu_grupo_familiar(cnu.Afiliado(65), [("padres", 88), ("conyuge", 63)], rp=0.03, agno_actual=2026)
    assert g.to_dict()["componentes"][2]["cnu"] == 0.135662
    assert cnu.faj_afiliado(65, rp=0.03, agno_vector=2013, agno_actual=2026) == pytest.approx(0.037205, abs=1e-6)
    assert cnu.faj_afiliado(65, 62, rp=0.03, agno_vector=2013, agno_actual=2026) == pytest.approx(0.004659, abs=1e-6)
    p = cnu.proyectar_pension(65, saldo=1000, rp=0.03, agno_actual=2026)
    assert p.pension[0] == pytest.approx(64.6979, abs=1e-4)
    assert p.descripcion == "Trayectoria de pension con banda 10% para afiliado soltero (tabla cb2020) tasa 3% en 2026."
    assert list(p.edad[p.acotado]) == [90, 91, 92, 93, 94, 95, 96, 97]
    assert p.pension[25] == pytest.approx(23.8114, abs=1e-4)
    q = cnu.proyectar_pension(65, saldo=1000, rp=0.03, agno_actual=2026, banda=False)
    assert q.acotado is None and q.pension[25] == pytest.approx(23.7923, abs=1e-4)
    assert cnu.VIGENCIA_BANDA == 20250901
    assert not cnu.proyectar_pension(65, saldo=1000, rp=0.03, agno_actual=2024).con_banda
    with pytest.warns(cnu.AdvertenciaCNU, match="21.419"):
        p = cnu.proyectar_pension(65, saldo=1000, rp=0.03, faj=True, agno_actual=2026)
    assert p.pension[0] == pytest.approx(63.2245, abs=1e-4)
    assert p.faj == pytest.approx(0.022775, abs=1e-6)
    c = cnu.calcular_cev(65, [("conyuge", 67, False)], pension_referencia=12, fecha_pension=20260301, rv=0.03)
    assert (c.factor, c.porcentaje, c.pension_referencia, c.compensacion, c.monto) == (1.091431, 1.0, 12, 1.097172, 1.10)
    assert (c.cnu_mujer, c.cnu_hombre, c.diferencia) == (18.498496, 16.948846, 0.091431)
    assert c.descripcion == ("CEV para mujer de 65 años pensionada el 20260301, grupo familiar: cónyuge sin hijos "
                             "(tablas rv2020m cb2020h / cb2020h), tasa 3%: factor 1.091431, 100% por edad")
    assert c.factor == round(
        cnu.cnu_grupo_familiar(cnu.Afiliado(65, True), [("conyuge", 67, False)], rv=0.03, fsiniestro=20260301).total
        / cnu.cnu_grupo_familiar(cnu.Afiliado(65, False), [("conyuge", 67, False)], rv=0.03, fsiniestro=20260301).total, 6)
    c = cnu.calcular_cev(62, [], pension_referencia=30, fecha_pension=20260301, rv=0.03)
    assert (c.factor, c.porcentaje, c.pension_referencia, c.monto) == (1.124605, 0.25, 18, 0.56)
    c = cnu.calcular_cev(65, [], pension_referencia=1, fecha_pension=20260301, rv=0.03)
    assert (c.compensacion, c.monto, c.minimo_aplicado) == (0.138914, 0.25, True)
    assert cnu.VIGENCIA_CEV == 20260102 and cnu.TOPE_PENSION_REFERENCIA_UF == 18 and cnu.MINIMO_CEV_UF == 0.25
    assert cnu.PORCENTAJE_CEV_POR_EDAD == {60: 0.05, 61: 0.15, 62: 0.25, 63: 0.5, 64: 0.75, 65: 1.0}
    with pytest.raises(cnu.ErrorCEV, match="mujeres"):
        cnu.calcular_cev(65, [], pension_referencia=12, fecha_pension=20260301, rv=0.03, mujer=False)
    with pytest.raises(cnu.ErrorCEV, match="20260102"):
        cnu.calcular_cev(65, [], pension_referencia=12, fecha_pension=20251201, rv=0.03)
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
    hijos = np.array([[10, 14, np.nan], [np.nan, np.nan, np.nan], [3, np.nan, np.nan]])
    v = cnu.cnu_grupo_familiar_vec(edades, [53, np.nan, 73], hijos, hijos_mujer=[[0, 1, 0]] * 3, rp=0.03, agno_actual=2026)
    np.testing.assert_allclose(v, [21.94064, 15.456439, 13.697482])
    assert v[0] == cnu.cnu_grupo_familiar(cnu.Afiliado(55), [("conyuge", 53), ("hijo", 10), ("hijo", 14, True)],
                                          rp=0.03, agno_actual=2026).total
    total, comp = cnu.cnu_grupo_familiar_vec(edades, [53, np.nan, 73], hijos, hijos_invalidez=[[0, 0, 0], [0, 0, 0], [2, 0, 0]],
                                             rp=0.03, agno_actual=2026, componentes=True)
    np.testing.assert_allclose(total, [21.940595, 15.456439, 15.030829])
    esperado = np.array([[19.728818, 2.132981, 0.052515, 0.026281, np.nan],
                         [15.456439, np.nan, np.nan, np.nan, np.nan],
                         [10.706354, 2.124165, 2.20031, np.nan, np.nan]])
    np.testing.assert_allclose(comp, esperado)
    assert comp.shape == (3, 5)


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
    assert main(["grupo", "--afiliado", "65", "--conyuge", "63", "--hijo", "10", "--rp", "0.03", "--agno-actual", "2026"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0] == ("CNU RP para grupo familiar: afiliado, cónyuge con hijos 50%/60%, hijo no inválido 15% "
                      "(tablas cb2020h b2020m), tasa 3% en el año 2026")
    assert [l.split()[-1] for l in out[1:]] == ["15.456439", "2.409035", "0.135662", "18.001136"]
    assert out[4].split()[0] == "total"
    assert main(["cev", "65", "--conyuge", "67h", "--pension", "12", "--fecha-pension", "20260301", "--rv", "0.03"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0] == ("CEV para mujer de 65 años pensionada el 20260301, grupo familiar: cónyuge sin hijos "
                      "(tablas rv2020m cb2020h / cb2020h), tasa 3%: factor 1.091431, 100% por edad")
    assert [l.split()[-1] for l in out[1:]] == ["18.498496", "16.948846", "1.091431", "100%", "12.000000", "1.097172", "1.10"]


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
    assert capsys.readouterr().out.strip() == f"cnu {cnu.__version__}" == "cnu 0.4.0"

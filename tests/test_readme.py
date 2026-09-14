"""Los ejemplos numericos del README se reproducen con el codigo."""

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
    assert cnu.faj_afiliado(65, rp=0.03, agno_vector=2013, agno_actual=2026) == pytest.approx(0.037205, abs=1e-6)
    assert cnu.faj_afiliado(65, 62, rp=0.03, agno_vector=2013, agno_actual=2026) == pytest.approx(0.004659, abs=1e-6)
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

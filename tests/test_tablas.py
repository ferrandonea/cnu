from pathlib import Path

import numpy as np
import pytest

import cnu
from cnu import tablas

RAIZ = Path(__file__).resolve().parent.parent
ADO = RAIZ / "ado"


@pytest.mark.skipif(not ADO.is_dir(), reason="requiere los binarios originales en ado/")
@pytest.mark.parametrize("nombre", sorted(p.name for p in ADO.glob("cnu_tabmor_*")) + sorted(p.name for p in ADO.glob("cnu_vec*")))
def test_binarios_mata_coinciden_con_csv(nombre):
    binario = tablas.leer_matriz_mata(ADO / nombre)
    csv = tablas._leer_empaquetado(nombre)
    assert csv is not None
    np.testing.assert_array_equal(binario, csv[0])


def test_roundtrip_binario_mata(tmp_path):
    m = np.array([[1.0, 0.5, 0.25], [2.0, 0.125, 0.0]])
    tablas.escribir_matriz_mata(tmp_path / "m", m, "prueba")
    np.testing.assert_array_equal(tablas.leer_matriz_mata(tmp_path / "m"), m)


def test_tabla_indexada_por_edad():
    rv = cnu.cargar_tabla_mortalidad("rv", 2009, "h")
    b = cnu.cargar_tabla_mortalidad("b", 2006, "m")
    assert rv.edades[0] == 1 and np.isnan(rv.qx[0])
    assert b.edades[0] == 0 and not np.isnan(b.qx[0])
    assert rv.qx[65] == pytest.approx(0.01244116)
    assert rv.nombre == "cnu_tabmor_rv2009h"


def test_mejoramiento():
    t = cnu.cargar_tabla_mortalidad("rv", 2009, "h")
    q = t.qx_mejorado(2011, 65)
    assert q[65] == pytest.approx(t.qx[65] * (1 - t.aa[65]) ** 2)
    assert q[70] == pytest.approx(t.qx[70] * (1 - t.aa[70]) ** 7)


def test_vector_tasas():
    v = cnu.cargar_vector_tasas(2013)
    assert v.shape == (191,)
    assert v[0] == pytest.approx(0.0443)
    assert tablas.existe_vector_tasas(2013)
    assert not tablas.existe_vector_tasas(1999)


def test_guardar_y_cargar_en_directorio(tmp_path):
    t = cnu.cargar_tabla_mortalidad("rv", 2009, "h")
    cnu.guardar_tabla_mortalidad(t, 2009, "h", "rv", tmp_path)
    with pytest.raises(FileExistsError):
        cnu.guardar_tabla_mortalidad(t, 2009, "h", "rv", tmp_path)
    cnu.guardar_tabla_mortalidad(t.como_matriz(), 2009, "h", "rv", tmp_path, reemplazar=True, formato="mata")
    t2 = cnu.cargar_tabla_mortalidad("rv", 2009, "h", str(tmp_path))
    np.testing.assert_allclose(t2.qx[1:], t.qx[1:])
    v = cnu.cargar_vector_tasas(2013)
    cnu.guardar_vector_tasas(v, 2013, tmp_path)
    np.testing.assert_array_equal(cnu.cargar_vector_tasas(2013, str(tmp_path)), v)
    # El mismo calculo con las tablas propias da el mismo resultado.
    assert cnu.cnu_afiliado(65, agno_actual=2013, dir_tablas=str(tmp_path), dir_vectores=str(tmp_path)) == pytest.approx(13.016880)


def test_directorio_inexistente():
    with pytest.raises(FileNotFoundError):
        cnu.cargar_tabla_mortalidad("rv", 2009, "h", "/no/existe")
    with pytest.raises(FileNotFoundError):
        cnu.cargar_tabla_mortalidad("rv", 1900, "h")


@pytest.mark.parametrize(
    "f, tipo, esperado",
    [
        (20050131, "rv", 1985), (20050201, "rv", 2004), (20100630, "rv", 2004), (20100701, "rv", 2009),
        (20080131, "b", 1985), (20080201, "b", 2006), (20080131, "mi", 1985), (20080201, "mi", 2006),
    ],
)
def test_agno_tabla_por_siniestro(f, tipo, esperado):
    assert cnu.agno_tabla_por_siniestro(f, tipo) == esperado


def test_parsear_nombre_tabla():
    assert tablas.parsear_nombre_tabla("rv2009") == ("rv", 2009)
    assert tablas.resolver_tabla("rv2009", fsiniestro=20040101) == ("rv", 1985)
    with pytest.raises(ValueError):
        tablas.parsear_nombre_tabla("2009")


def test_listados():
    assert "cnu_tabmor_rv2009h" in cnu.tablas_disponibles()
    assert cnu.vectores_disponibles() == [2009, 2010, 2011, 2012, 2013]


# ---------------------------------------------------------------------------
# TM2014 / TM2020 (factores bidimensionales) y tipo cb
# ---------------------------------------------------------------------------
TM2020 = [("cb", "h"), ("rv", "m"), ("b", "m"), ("mi", "h"), ("mi", "m")]


@pytest.mark.parametrize("tipo, genero", TM2020)
def test_cargar_tm2020(tipo, genero):
    t = cnu.cargar_tabla_mortalidad(tipo, 2020, genero)
    assert t.bidimensional
    assert t.agnos_aa == tuple(range(2021, 2037))
    assert t.aa.shape == (111, 16)
    assert t.qx.shape == (111,)
    edad_min = 20 if tipo == "rv" else 0
    assert int(t.edades.min()) == edad_min and int(t.edades.max()) == 110
    assert not np.isnan(t.qx[edad_min]) and not np.isnan(t.aa[edad_min]).any()
    if edad_min:
        assert np.isnan(t.qx[0]) and np.isnan(t.aa[0]).all()


def test_valores_tm2020():
    t = cnu.cargar_tabla_mortalidad("cb", 2020, "h")
    assert t.qx[0] == pytest.approx(0.00615389)
    assert t.aa[0, 0] == pytest.approx(0.039574)  # aa2021
    assert t.aa[0, 1] == pytest.approx(0.037487)  # aa2022
    assert t.cabecera_csv[:3] == ("edad", "qx", "aa2021")


@pytest.mark.parametrize("tipo, genero", [("cb", "h"), ("rv", "m"), ("b", "m"), ("mi", "h"), ("mi", "m")])
def test_cargar_tm2014_historicas(tipo, genero):
    t = cnu.cargar_tabla_mortalidad(tipo, 2014, genero)
    assert not t.bidimensional and t.agnos_aa is None
    assert t.aa.ndim == 1
    assert t.cabecera_csv == ("edad", "qx", "aa")


def test_tipo_cb_solo_hombres():
    assert cnu.cargar_tabla_mortalidad("cb", 2014, "h").nombre == "cnu_tabmor_cb2014h"
    with pytest.raises(ValueError, match="solo existe para hombres"):
        cnu.cargar_tabla_mortalidad("cb", 2014, "m")
    with pytest.raises(ValueError, match="no permitido"):
        cnu.cargar_tabla_mortalidad("xx", 2014, "h")


def test_roundtrip_csv_bidimensional(tmp_path):
    t = cnu.cargar_tabla_mortalidad("cb", 2020, "h")
    ruta = cnu.guardar_tabla_mortalidad(t, 2020, "h", "cb", tmp_path)
    assert ruta.read_text().splitlines()[0] == "edad,qx," + ",".join(f"aa{a}" for a in range(2021, 2037))
    t2 = cnu.cargar_tabla_mortalidad("cb", 2020, "h", str(tmp_path))
    assert t2.agnos_aa == t.agnos_aa
    np.testing.assert_array_equal(t2.edades, t.edades)
    np.testing.assert_allclose(t2.qx, t.qx)
    np.testing.assert_allclose(t2.aa, t.aa)
    # Una matriz cruda con mas de tres columnas exige los agnos.
    with pytest.raises(ValueError, match="agnos_aa"):
        cnu.guardar_tabla_mortalidad(t.como_matriz(), 2020, "h", "cb", tmp_path, reemplazar=True)
    cnu.guardar_tabla_mortalidad(t.como_matriz(), 2020, "h", "cb", tmp_path, reemplazar=True, agnos_aa=t.agnos_aa)
    assert cnu.cargar_tabla_mortalidad("cb", 2020, "h", str(tmp_path)).bidimensional


def test_desde_matriz_exige_agnos():
    m = np.array([[65.0, 0.01, 0.02, 0.03], [66.0, 0.011, 0.021, 0.031]])
    with pytest.raises(ValueError, match="agnos_aa"):
        cnu.TablaMortalidad.desde_matriz("cb", 2020, "h", m)
    with pytest.raises(ValueError, match="2 columnas de factores"):
        cnu.TablaMortalidad.desde_matriz("cb", 2020, "h", m, agnos_aa=[2021])
    t = cnu.TablaMortalidad.desde_matriz("cb", 2020, "h", m, agnos_aa=[2021, 2022])
    assert t.bidimensional and t.agnos_aa == (2021, 2022)
    assert t.aa[66, 1] == pytest.approx(0.031)
    np.testing.assert_array_equal(t.como_matriz(), m)
    # El mejoramiento bidimensional llega en el issue #4.
    with pytest.raises(NotImplementedError):
        t.qx_mejorado(2024, 65)


def test_binario_mata_bidimensional_exige_agnos(tmp_path):
    t = cnu.cargar_tabla_mortalidad("cb", 2020, "h")
    cnu.guardar_tabla_mortalidad(t, 2020, "h", "cb", tmp_path, formato="mata")
    with pytest.raises(ValueError, match="agnos_aa"):
        cnu.cargar_tabla_mortalidad("cb", 2020, "h", str(tmp_path))


def test_cabecera():
    assert tablas.agnos_desde_cabecera(["edad", "qx", "aa"]) is None
    assert tablas.agnos_desde_cabecera(["edad", "qx", "aa2021", "aa2022"]) == (2021, 2022)
    with pytest.raises(ValueError):
        tablas.agnos_desde_cabecera(["edad", "qx", "factor"])


def test_listado_incluye_2014_y_2020():
    disponibles = cnu.tablas_disponibles()
    for n in ("cnu_tabmor_cb2014h", "cnu_tabmor_cb2020h", "cnu_tabmor_rv2020m", "cnu_tabmor_b2020m", "cnu_tabmor_mi2020m"):
        assert n in disponibles
    assert "bidimensionales 2021-2036" in tablas.describir_tabla("cnu_tabmor_cb2020h")
    assert "historico" in tablas.describir_tabla("cnu_tabmor_rv2009h")

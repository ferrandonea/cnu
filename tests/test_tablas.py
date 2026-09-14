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
    np.testing.assert_array_equal(binario, csv)


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

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
    assert cnu.cnu_afiliado(65, agno_vector=2013, agno_actual=2013, dir_tablas=str(tmp_path), dir_vectores=str(tmp_path)) == pytest.approx(13.016880)


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
        # Vigencias nuevas (2016 y 2023).
        (20160630, "rv", 2009), (20160701, "rv", 2014), (20230630, "rv", 2014), (20230701, "rv", 2020),
        (20160630, "b", 2006), (20160701, "b", 2014), (20230630, "b", 2014), (20230701, "b", 2020),
        (20160630, "mi", 2006), (20160701, "mi", 2014), (20230630, "mi", 2014), (20230701, "mi", 2020),
    ],
)
def test_agno_tabla_por_siniestro(f, tipo, esperado):
    assert cnu.agno_tabla_por_siniestro(f, tipo) == esperado


# Fronteras de vigencia: (fecha, afiliado h, afiliado m, benef h, benef m, invalido h/m).
_VIGENCIAS = [
    (19900101, "rv1985", "rv1985", "b1985", "b1985", "mi1985"),
    (20050131, "rv1985", "rv1985", "b1985", "b1985", "mi1985"),
    (20050201, "rv2004", "rv2004", "b1985", "b1985", "mi1985"),
    (20080131, "rv2004", "rv2004", "b1985", "b1985", "mi1985"),
    (20080201, "rv2004", "rv2004", "b2006", "b2006", "mi2006"),
    (20100630, "rv2004", "rv2004", "b2006", "b2006", "mi2006"),
    (20100701, "rv2009", "rv2009", "b2006", "b2006", "mi2006"),
    (20160630, "rv2009", "rv2009", "b2006", "b2006", "mi2006"),
    (20160701, "cb2014", "rv2014", "cb2014", "b2014", "mi2014"),
    (20230630, "cb2014", "rv2014", "cb2014", "b2014", "mi2014"),
    (20230701, "cb2020", "rv2020", "cb2020", "b2020", "mi2020"),
    (20240101, "cb2020", "rv2020", "cb2020", "b2020", "mi2020"),
]


@pytest.mark.parametrize("f, afil_h, afil_m, benef_h, benef_m, inv", _VIGENCIAS)
def test_tabla_por_fecha(f, afil_h, afil_m, benef_h, benef_m, inv):
    def nombre(rol, genero):
        tipo, agno = cnu.tabla_por_fecha(f, rol, genero)
        return f"{tipo}{agno}"

    assert nombre("rv", "h") == afil_h
    assert nombre("rv", "m") == afil_m
    assert nombre("b", "h") == benef_h
    assert nombre("b", "m") == benef_m
    assert nombre("mi", "h") == inv
    assert nombre("mi", "m") == inv


def test_tabla_por_fecha_valida_argumentos():
    with pytest.raises(ValueError, match="Rol"):
        cnu.tabla_por_fecha(20240101, "cb", "h")
    with pytest.raises(ValueError, match="Genero"):
        cnu.tabla_por_fecha(20240101, "rv", "x")


def test_resolver_tabla_con_rol_y_genero():
    # Con rol y genero cambia tambien el tipo (cb para hombres desde 2016).
    assert tablas.resolver_tabla("rv2009", 20240101, "rv", "h") == ("cb", 2020)
    assert tablas.resolver_tabla("rv2009", 20240101, "rv", "m") == ("rv", 2020)
    assert tablas.resolver_tabla("b2006", 20240101, "b", "h") == ("cb", 2020)
    assert tablas.resolver_tabla("b2006", 20240101, "b", "m") == ("b", 2020)
    # Sin fsiniestro se respeta la tabla explicita.
    assert tablas.resolver_tabla("rv2009", 0, "rv", "h") == ("rv", 2009)


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
    # Mejoramiento bidimensional: 65 en 2024 acumula 2021..2022 y repite el ultimo factor.
    q = t.qx_mejorado(2024, 65)
    assert q[65] == pytest.approx(0.01 * (1 - 0.02) * (1 - 0.03) ** 3)
    assert q[66] == pytest.approx(0.011 * (1 - 0.021) * (1 - 0.031) ** 4)


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


def test_mejoramiento_bidimensional_ejemplo_oficial():
    # Anexo N 9 de la SP: CB-H-2020, edad 65, agno 2022.
    t = cnu.cargar_tabla_mortalidad("cb", 2020, "h")
    q = t.qx_mejorado(2022, 65)
    assert q[65] == pytest.approx(0.00852603117, abs=1e-9)
    assert q[65] == pytest.approx(t.qx[65] * (1 - t.aa[65, 0]) * (1 - t.aa[65, 1]))


def test_mejoramiento_bidimensional_edad_futura():
    # Desde 65 en 2022, la edad 70 se evalua en 2027: factores de la fila 70 de 2021 a 2027.
    t = cnu.cargar_tabla_mortalidad("cb", 2020, "h")
    q = t.qx_mejorado(2022, 65)
    assert q[70] == pytest.approx(t.qx[70] * np.prod(1 - t.aa[70, :7]))
    # Edades anteriores a 2021 no se mejoran (producto vacio).
    assert q[60] == pytest.approx(t.qx[60])


def test_mejoramiento_bidimensional_repite_2036():
    t = cnu.cargar_tabla_mortalidad("cb", 2020, "h")
    q36 = t.qx_mejorado(2036, 65)
    q37 = t.qx_mejorado(2037, 65)
    np.testing.assert_allclose(q37[65:], q36[65:] * (1 - t.aa[65:, -1]))
    assert q36[65] == pytest.approx(t.qx[65] * np.prod(1 - t.aa[65, :]))


def test_mejoramiento_bidimensional_agno_base():
    t = cnu.cargar_tabla_mortalidad("cb", 2020, "h")
    q = t.qx_mejorado(2020, 65)
    assert q[65] == t.qx[65]
    np.testing.assert_array_equal(q[:66], t.qx[:66])
    # En 2020 las edades futuras si acumulan mejoramiento (66 se evalua en 2021).
    assert q[66] == pytest.approx(t.qx[66] * (1 - t.aa[66, 0]))

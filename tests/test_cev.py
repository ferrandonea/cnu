"""Compensacion por Diferencias de Expectativa de Vida (Ley N 21.735, Titulo
XIX, Letra C): factor como razon de dos grupos familiares, porcentaje por
edad, tope de 18 UF, minimo de 0,25 UF y errores."""

import pytest

import cnu

K = dict(fecha_pension=20260301, rv=0.03)
CONYUGE = [("conyuge", 67, False)]


def _grupo(edad, beneficiarios, mujer):
    return cnu.cnu_grupo_familiar(cnu.Afiliado(edad, mujer), beneficiarios, rv=0.03, fsiniestro=20260301,
                                  agno_actual=2026)


def test_factor_es_la_razon_de_dos_grupos_familiares_mujer_y_hombre():
    r = cnu.calcular_cev(65, CONYUGE, pension_referencia=12, **K)
    assert isinstance(r, cnu.ResultadoCEV)
    mujer, hombre = _grupo(65, CONYUGE, True), _grupo(65, CONYUGE, False)
    assert r.factor == round(mujer.total / hombre.total, 6) == 1.091431
    assert r.cnu_mujer == mujer.total == 18.498496 and r.cnu_hombre == hombre.total == 16.948846
    assert r.grupo_mujer.tablas == ("rv2020m", "cb2020h") and r.grupo_hombre.tablas == ("cb2020h",)
    assert r.diferencia == round(r.factor - 1, 6) == 0.091431
    # El sexo de cada beneficiario se conserva en ambos CNU (el conyuge hombre sigue con tabla de hombre).
    assert r.grupo_hombre.componentes[1].cnu == cnu.cnu_conyuge(65, 67, cony_mujer=False, rv=0.03, agno_actual=2026)
    # Grupo con hijos: mismos tramos del articulo 58 en ambos.
    h = cnu.calcular_cev(65, [("conyuge", 67, False), ("hijo", 10)], pension_referencia=12, **K)
    assert [c.etiqueta for c in h.grupo_hombre.componentes] == [c.etiqueta for c in h.grupo_mujer.componentes]
    assert h.factor == round(_grupo(65, [("conyuge", 67, False), ("hijo", 10)], True).total
                             / _grupo(65, [("conyuge", 67, False), ("hijo", 10)], False).total, 6)


def test_monto_tope_y_minimo():
    r = cnu.calcular_cev(65, CONYUGE, pension_referencia=12, **K)
    assert r.porcentaje == 1.0 and r.pension_referencia == 12
    assert r.compensacion == round(12 * (r.factor - 1) * 1.0, 6) == 1.097172
    assert r.monto == 1.10 and not r.minimo_aplicado
    # Tope: la pension de referencia se acota a 18 UF.
    t = cnu.calcular_cev(65, CONYUGE, pension_referencia=30, **K)
    assert t.pension_referencia == cnu.TOPE_PENSION_REFERENCIA_UF == 18
    assert t.monto == cnu.calcular_cev(65, CONYUGE, pension_referencia=18, **K).monto == 1.65
    # Minimo: 0,25 UF aunque la compensacion calculada sea menor.
    m = cnu.calcular_cev(65, [], pension_referencia=1, **K)
    assert m.compensacion == 0.138914 and m.monto == cnu.MINIMO_CEV_UF == 0.25 and m.minimo_aplicado
    assert cnu.calcular_cev(65, [], pension_referencia=0.01, **K).monto == 0.25
    # El monto se expresa en UF con dos decimales.
    assert cnu.calcular_cev(62, [], pension_referencia=30, **K).monto == 0.56


def test_porcentaje_por_edad():
    assert cnu.PORCENTAJE_CEV_POR_EDAD == {60: 0.05, 61: 0.15, 62: 0.25, 63: 0.50, 64: 0.75, 65: 1.0}
    assert cnu.EDAD_CEV == 65
    assert [cnu.porcentaje_cev(e) for e in (60, 61, 62, 63, 64, 65, 66, 70)] == [0.05, 0.15, 0.25, 0.5, 0.75, 1, 1, 1]
    assert cnu.porcentaje_cev(64.5) == 1.0 and cnu.porcentaje_cev(64.4) == 0.75  # edad actuarial
    with pytest.raises(cnu.ErrorCEV, match="articulo 68"):
        cnu.porcentaje_cev(59)
    r = cnu.calcular_cev(62, [], pension_referencia=18, **K)
    assert r.porcentaje == 0.25 and r.edad == 62
    assert r.compensacion == round(18 * (r.factor - 1) * 0.25, 6)
    # A los 65 el porcentaje es 100% y el factor usa la edad de pension en ambos CNU.
    r = cnu.calcular_cev(70, [], pension_referencia=18, **K)
    assert r.porcentaje == 1.0 and r.cnu_mujer == cnu.cnu_afiliado(70, mujer=True, rv=0.03, agno_actual=2026)
    assert cnu.calcular_cev(64.6, [], pension_referencia=18, **K).edad == 65


def test_errores_claros():
    with pytest.raises(cnu.ErrorCEV, match="solo corresponde a mujeres"):
        cnu.calcular_cev(65, CONYUGE, pension_referencia=12, mujer=False, **K)
    assert cnu.VIGENCIA_CEV == 20260102
    with pytest.raises(cnu.ErrorCEV, match="20260102"):
        cnu.calcular_cev(65, CONYUGE, pension_referencia=12, fecha_pension=20260101, rv=0.03)
    with pytest.raises(cnu.ErrorCEV, match="fecha de pension"):
        cnu.calcular_cev(65, CONYUGE, pension_referencia=12, rv=0.03)
    with pytest.raises(cnu.ErrorCEV, match="articulo 68"):
        cnu.calcular_cev(59, CONYUGE, pension_referencia=12, **K)
    with pytest.raises(cnu.ErrorCEV, match="igual o menor que cero"):
        cnu.calcular_cev(65, CONYUGE, pension_referencia=0, **K)
    with pytest.raises(cnu.ErrorCEV, match="rv"):
        cnu.calcular_cev(65, CONYUGE, pension_referencia=12, fecha_pension=20260301)
    assert issubclass(cnu.ErrorCEV, ValueError)
    # Las exclusiones del grupo familiar se propagan.
    with pytest.raises(cnu.ErrorGrupoFamiliar, match="articulo 58"):
        cnu.calcular_cev(65, [("padres", 88), ("conyuge", 67, False)], pension_referencia=12, **K)
    # Justo en la vigencia se calcula.
    assert cnu.calcular_cev(65, [], pension_referencia=12, fecha_pension=20260102, rv=0.03).monto > 0


def test_descripcion_y_to_dict():
    r = cnu.calcular_cev(65, CONYUGE, pension_referencia=12, **K)
    assert r.descripcion == ("CEV para mujer de 65 años pensionada el 20260301, grupo familiar: cónyuge sin hijos "
                             "(tablas rv2020m cb2020h / cb2020h), tasa 3%: factor 1.091431, 100% por edad")
    d = r.to_dict()
    assert d["monto"] == 1.10 and d["factor"] == 1.091431 and d["diferencia"] == 0.091431
    assert d["grupo_mujer"]["total"] == 18.498496 and d["grupo_hombre"]["componentes"][0]["tablas"] == ["cb2020h"]
    assert "sin beneficiarios" in cnu.calcular_cev(65, [], pension_referencia=12, **K).descripcion


def test_pasos_imprime_ambos_cnu(capsys):
    cnu.calcular_cev(65, [], pension_referencia=12, pasos=True, **K)
    out = capsys.readouterr().out
    assert "=== CNU mujer ===" in out and "=== CNU hombre de igual edad ===" in out
    assert "tabla rv2020m" in out and "tabla cb2020h" in out

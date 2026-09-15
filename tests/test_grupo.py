"""Grupo familiar del Anexo N 7: total como suma de componentes, tramos
automaticos del articulo 58, exclusiones y cuota mortuoria."""

import pytest

import cnu

K = dict(rp=0.03, agno_actual=2026)
A, B = cnu.Afiliado, cnu.Beneficiario


def _suma(r):
    return round(sum(c.cnu for c in r.componentes), 6)


def test_grupo_es_suma_exacta_y_componentes_coinciden_con_funciones_individuales():
    r = cnu.cnu_grupo_familiar(A(65), [B("conyuge", 63), B("hijo", 10), B("hijo", 14, True)], **K)
    assert isinstance(r, cnu.CNUGrupoFamiliar) and r.total == _suma(r) == 18.066759
    tipos = [c.tipo for c in r.componentes]
    assert tipos == ["afiliado", "conyuge", "hijo", "hijo"]
    valores = [c.cnu for c in r.componentes]
    assert valores == [
        cnu.cnu_afiliado(65, **K),
        cnu.cnu_conyuge_con_hijos(65, 63, 10, **K),  # el hijo menor (10) fija el tramo 50%/60%
        cnu.cnu_hijo(65, 10, **K),
        cnu.cnu_hijo(65, 14, hijo_mujer=True, **K),
    ]
    assert r.componentes[1].porcentajes == (0.5, 0.6) and r.componentes[2].porcentajes == (0.15,)
    assert r.componentes[1].etiqueta == "cónyuge con hijos 50%/60%"
    assert r.componentes[3].tablas == ("cb2020h", "b2020m")
    assert r.tablas == ("cb2020h", "b2020m")
    assert not r.sobrevivencia


def test_solo_afiliado_coincide_con_cnu_afiliado():
    r = cnu.cnu_grupo_familiar(A(65), [], **K)
    assert r.total == cnu.cnu_afiliado(65, **K) == 15.456439
    assert [c.tipo for c in r.componentes] == ["afiliado"] and r.componentes[0].porcentajes == (1.0,)
    r = cnu.cnu_grupo_familiar(A(60, mujer=True), **K)
    assert r.total == cnu.cnu_afiliado(60, mujer=True, **K)
    # El afiliado tambien se acepta como tupla o como edad (hombre).
    assert cnu.cnu_grupo_familiar((60, True), **K).total == r.total
    assert cnu.cnu_grupo_familiar(65, **K).total == 15.456439


def test_conyuge_sin_hijos_conviviente_y_hijos_sin_derecho():
    r = cnu.cnu_grupo_familiar(A(65), [B("conyuge", 63)], **K)
    assert r.componentes[1].cnu == cnu.cnu_conyuge(65, 63, **K) == 2.493278
    assert r.componentes[1].porcentajes == (0.6,) and r.componentes[1].etiqueta == "cónyuge sin hijos"
    # Conviviente civil: mismo valor que el conyuge, con su nombre.
    c = cnu.cnu_grupo_familiar(A(65), [B("conviviente", 63)], **K)
    assert c.total == r.total and c.componentes[1].tipo == "conviviente"
    assert c.componentes[1].etiqueta == "conviviente civil sin hijos"
    # Un hijo de 24 o mas no tiene derecho: aporta 0 y el conyuge queda como sin hijos.
    h = cnu.cnu_grupo_familiar(A(65), [B("conyuge", 63), B("hijo", 30)], **K)
    assert h.componentes[1].cnu == 2.493278 and h.componentes[1].porcentajes == (0.6,)
    assert h.componentes[2].cnu == 0.0 and h.componentes[2].porcentajes == (0.0,)
    assert "sin derecho" in h.componentes[2].etiqueta
    assert h.total == r.total
    # Conyuge hombre de afiliada mujer.
    m = cnu.cnu_grupo_familiar(A(60, True), [B("conyuge", 65, False)], **K)
    assert m.componentes[1].cnu == cnu.cnu_conyuge(60, 65, cot_mujer=True, cony_mujer=False, **K)
    assert m.componentes[1].tablas == ("rv2020m", "cb2020h")


def test_tramos_desde_la_lista():
    # El hijo menor con derecho fija el cambio 50% -> 60% y 30% -> 36%.
    r = cnu.cnu_grupo_familiar(A(50), [B("conyuge", 48), B("madre_padre", 45), B("hijo", 21), B("hijo", 5)], **K)
    assert r.componentes[1].cnu == cnu.cnu_conyuge_con_hijos(50, 48, 5, **K)
    assert r.componentes[2].cnu == cnu.cnu_madre_padre(50, 45, 5, **K)
    assert r.componentes[2].porcentajes == (0.30, 0.36)
    assert r.componentes[2].etiqueta == "madre no matrimonial con hijos 30%/36%"
    # Un hijo invalido fija 50% y 30% vitalicios, cualquiera sea la edad de los demas.
    i = cnu.cnu_grupo_familiar(A(50), [B("conyuge", 48), B("madre_padre", 45, False), B("hijo", 5),
                                       B("hijo_invalido", 30, parcial=True)], **K)
    assert i.componentes[1].cnu == cnu.cnu_conyuge_con_hijos(50, 48, 5, hijo_invalido=True, **K)
    assert i.componentes[1].porcentajes == (0.5,) and i.componentes[1].etiqueta == "cónyuge con hijo inválido 50%"
    assert i.componentes[2].cnu == cnu.cnu_madre_padre(50, 45, madre=False, hijo_invalido=True, **K)
    assert i.componentes[2].porcentajes == (0.30,) and i.componentes[2].etiqueta == "padre no matrimonial con hijo inválido 30%"
    assert i.componentes[4].cnu == cnu.cnu_hijo_invalido(50, 30, parcial=True, **K)
    assert i.componentes[4].porcentajes == (0.11,)  # parcial de 24 o mas: 11% vitalicio
    p = cnu.cnu_grupo_familiar(A(50), [B("conyuge", 48), B("hijo_invalido", 20, True, True)], **K)
    assert p.componentes[2].porcentajes == (0.15, 0.11) and p.componentes[2].etiqueta == "hijo inválido parcial 15%/11%"
    assert p.componentes[2].cnu == cnu.cnu_hijo_invalido(50, 20, hijo_mujer=True, parcial=True, **K)
    assert p.componentes[2].tablas == ("cb2020h", "mi2020m")
    # Sin hijos con derecho, madre o padre no matrimonial al 36% vitalicio.
    s = cnu.cnu_grupo_familiar(A(50), [B("madre_padre", 45)], **K)
    assert s.componentes[1].cnu == cnu.cnu_madre_padre(50, 45, **K) == 1.370831
    assert s.componentes[1].porcentajes == (0.36,)
    # Cónyuge con hijos <= cónyuge sin hijos.
    con = cnu.cnu_grupo_familiar(A(65), [B("conyuge", 63), B("hijo", 10)], **K)
    sin = cnu.cnu_grupo_familiar(A(65), [B("conyuge", 63)], **K)
    assert con.componentes[1].cnu < sin.componentes[1].cnu


def test_padres_del_afiliado():
    r = cnu.cnu_grupo_familiar(A(65), [B("padres", 88), B("padres", 90, False)], **K)
    assert [c.cnu for c in r.componentes] == [
        cnu.cnu_afiliado(65, **K), cnu.cnu_padres(65, 88, **K), cnu.cnu_padres(65, 90, madre=False, **K),
    ]
    assert [c.etiqueta for c in r.componentes[1:]] == ["madre del afiliado 50%", "padre del afiliado 50%"]
    assert r.componentes[1].porcentajes == (0.5,)
    s = cnu.cnu_grupo_familiar(None, [B("padres", 88)], **K)
    assert s.componentes[0].cnu == cnu.cnu_sobrevivencia_padres(88, **K) == 3.089039
    assert s.componentes[0].etiqueta == "madre del causante 50%"


def test_sobrevivencia_usa_las_variantes_de_sobrevivencia():
    r = cnu.cnu_grupo_familiar(None, [B("conyuge", 63), B("hijo", 10, True), B("hijo_invalido", 21, True),
                                      B("madre_padre", 45)], **K)
    assert r.sobrevivencia and [c.tipo for c in r.componentes] == ["conyuge", "hijo", "hijo_invalido", "madre_padre"]
    assert [c.cnu for c in r.componentes] == [
        cnu.cnu_sobrevivencia_conyuge_con_hijos(63, 10, mujer=True, hijo_invalido=True, **K),
        cnu.cnu_sobrevivencia_hijo(10, mujer=True, **K),
        cnu.cnu_sobrevivencia_hijo_invalido(21, mujer=True, **K),
        cnu.cnu_sobrevivencia_madre_padre(45, 10, hijo_invalido=True, **K),
    ]
    assert r.total == _suma(r)
    assert r.descripcion.startswith("CNU RP para sobrevivencia de grupo familiar: cónyuge con hijo inválido 50%, "
                                    "hijo no inválido 15%, hijo inválido total 15%, madre no matrimonial con hijo inválido 30%"
                                    " (tablas b2020m mi2020m)")
    s = cnu.cnu_grupo_familiar(None, [B("conviviente", 63, True)], **K)
    assert s.total == cnu.cnu_sobrevivencia_conyuge(63, mujer=True, **K) == 10.674379
    assert s.componentes[0].etiqueta == "conviviente civil sin hijos"
    s = cnu.cnu_grupo_familiar(None, [B("conyuge", 63), B("hijo", 10, True)], **K)
    assert s.total == 11.298419


@pytest.mark.parametrize("afiliado, beneficiarios, mensaje", [
    (A(65), [B("padres", 88), B("conyuge", 63)], "articulo 58"),
    (A(65), [B("padres", 88), B("conviviente", 63)], "articulo 58"),
    (A(65), [B("padres", 88), B("hijo", 10)], "articulo 58"),
    (A(65), [B("padres", 88), B("hijo_invalido", 30)], "articulo 58"),
    (A(65), [B("padres", 88), B("madre_padre", 45)], "articulo 58"),
    (None, [B("padres", 88), B("hijo", 10)], "articulo 58"),
    (A(65), [B("padres", 88), B("padres", 85)], "una madre y un padre"),
    (A(65), [B("conyuge", 63), B("conyuge", 60)], "a lo mas un conyuge"),
    (A(65), [B("conyuge", 63), B("conviviente", 60)], "a lo mas un conyuge"),
    (A(65), [B("hijo", 10)], "0,5/n"),
    (A(65), [B("hijo_invalido", 30)], "0,5/n"),
    (None, [B("hijo", 10), B("hijo", 5)], "0,5/n"),
    (A(65), [B("tio", 40)], "desconocido"),
    (A(65), [B("hijo", 10, parcial=True)], "solo aplica al hijo invalido"),
    (None, [], "sin beneficiarios"),
])
def test_combinaciones_no_admitidas_fallan_con_valueerror_que_cita_la_regla(afiliado, beneficiarios, mensaje):
    with pytest.raises(cnu.ErrorGrupoFamiliar, match=mensaje) as e:
        cnu.cnu_grupo_familiar(afiliado, beneficiarios, **K)
    assert isinstance(e.value, ValueError)
    if mensaje == "articulo 58":
        assert "padres" in str(e.value).lower()


def test_hijos_sin_derecho_no_exigen_conyuge():
    """Un hijo de 24 o mas no tiene derecho, asi que no rige la regla 0,5/n."""
    r = cnu.cnu_grupo_familiar(A(65), [B("hijo", 30)], **K)
    assert r.total == cnu.cnu_afiliado(65, **K) and r.componentes[1].cnu == 0.0


def test_cuota_mortuoria():
    assert cnu.CUOTA_MORTUORIA_UF == 15 and "CUOTA_MORTUORIA_UF" in cnu.__all__
    sin = cnu.cnu_grupo_familiar(A(65), [B("conyuge", 63), B("hijo", 10)], **K)
    con = cnu.cnu_grupo_familiar(A(65), [B("conyuge", 63), B("hijo", 10)], valor_uf=39000.5, **K)
    assert con.componentes[-1].tipo == "cuota_mortuoria" and con.componentes[-1].etiqueta == "cuota mortuoria 15 UF"
    assert con.componentes[-1].cnu == round(15 * 39000.5, 6) and con.componentes[-1].porcentajes == ()
    assert con.total == round(sin.total + 15 * 39000.5, 6) == _suma(con)
    assert [c.cnu for c in con.componentes[:-1]] == [c.cnu for c in sin.componentes]
    assert "cuota mortuoria 15 UF" in con.descripcion and "cuota" not in sin.descripcion
    uf = cnu.cnu_grupo_familiar(A(65), [B("conyuge", 63), B("hijo", 10)], valor_uf=1, **K)
    assert uf.total == 33.001136


def test_describir_acepta_el_grupo_y_to_dict():
    r = cnu.cnu_grupo_familiar(A(65), [B("conyuge", 63), B("hijo", 10), B("hijo_invalido", 20)], **K)
    assert r.descripcion == cnu.describir(r, rp=0.03, agno_actual=2026) == (
        "CNU RP para grupo familiar: afiliado, cónyuge con hijo inválido 50%, hijo no inválido 15%, "
        "hijo inválido total 15% (tablas cb2020h b2020m mi2020h), tasa 3% en el año 2026"
    )
    assert cnu.describir(r, rv=0.032, agno_actual=2026).startswith("CNU RV para grupo familiar: afiliado, ")
    d = r.to_dict()
    assert d["total"] == r.total and d["descripcion"] == r.descripcion and d["sobrevivencia"] is False
    assert d["componentes"][1] == {"tipo": "conyuge", "etiqueta": "cónyuge con hijo inválido 50%", "porcentajes": [0.5],
                                   "cnu": r.componentes[1].cnu, "tablas": ["cb2020h", "b2020m"]}
    assert sum(c["cnu"] for c in d["componentes"]) == pytest.approx(d["total"], abs=1e-6)


def test_misma_regla_de_tasa_tabla_y_edad_actuarial():
    with pytest.raises(ValueError, match="TITRP"):
        cnu.cnu_grupo_familiar(A(65), [B("conyuge", 63)], agno_actual=2026)
    r = cnu.cnu_grupo_familiar(A(65), [B("conyuge", 63), B("hijo", 10)], fsiniestro=20130101, rp=0.03, agno_actual=2026)
    assert r.componentes[1].cnu == cnu.cnu_conyuge_con_hijos(65, 63, 10, tabla="rv2009", tabla_benef="b2006", rp=0.03,
                                                             agno_actual=2026)
    assert r.tablas == ("rv2009h", "b2006m", "b2006h")
    assert cnu.cnu_grupo_familiar(A(64.5), [B("conyuge", 62.6), B("hijo", 9.5)], **K).total == (
        cnu.cnu_grupo_familiar(A(65), [B("conyuge", 63), B("hijo", 10)], **K).total
    )
    v = cnu.cnu_grupo_familiar(A(65), [B("conyuge", 63)], agno_vector=2013, agno_actual=2013)
    assert v.descripcion.endswith("vector 2013 en el año 2013")
    # Beneficiarios como tuplas o diccionarios.
    t = cnu.cnu_grupo_familiar(A(65), [("conyuge", 63), {"tipo": "hijo", "edad": 10, "mujer": True}], **K)
    assert t.total == cnu.cnu_grupo_familiar(A(65), [B("conyuge", 63), B("hijo", 10, True)], **K).total


def test_pasos_imprime_cada_componente(capsys):
    cnu.cnu_grupo_familiar(A(65), [B("conyuge", 63), B("hijo", 10)], valor_uf=1, pasos=True, **K)
    out = capsys.readouterr().out
    assert out.count("--- ") == 4 and "--- cónyuge con hijos 50%/60% ---" in out and "t =   1:" in out
    assert "cuota mortuoria: 15 UF * 1 = 15" in out


def test_api_publica():
    for nombre in ("cnu_grupo_familiar", "Afiliado", "Beneficiario", "CNUGrupoFamiliar", "ComponenteCNU",
                   "ErrorGrupoFamiliar", "CUOTA_MORTUORIA_UF", "TIPOS_BENEFICIARIO"):
        assert nombre in cnu.__all__
    assert cnu.TIPOS_BENEFICIARIO == ("conyuge", "conviviente", "hijo", "hijo_invalido", "madre_padre", "padres")
    assert B("conyuge", 63).es_mujer and not B("hijo", 10).es_mujer and B("padres", 88).es_mujer
    assert not B("madre_padre", 45, False).es_mujer

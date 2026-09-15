"""Valores de referencia documentados en la ayuda de Stata (cnu.sthlp).

Los ejemplos de ``cnu_afili`` en la ayuda fueron generados con una version
anterior del modulo (se nota en el formato de la etiqueta), y difieren de la
implementacion Mata final en hasta 5e-6; los valores de ``cnu_cnyg_s_hi`` y
``cnu_faji`` coinciden exactamente a 6 decimales.
"""

import numpy as np
import pytest

import cnu


@pytest.mark.parametrize(
    "kwargs, esperado",
    [
        # . cnu_afili 65                     (vector 2013 en el año 2013)
        (dict(x=65, agno_vector=2013, agno_actual=2013), 13.016880),  # obtenido: 13.016877
        # . cnu_afili 65, rp(.0366)          (tasa 3.66% en el año 2014)
        (dict(x=65, rp=0.0366, agno_actual=2014), 13.377540),  # obtenido: 13.377535
        # . cnu_afili 65, agnoa(2011) agnov(2011)
        (dict(x=65, agno_vector=2011, agno_actual=2011), 12.862230),  # obtenido: 12.862231
    ],
)
def test_cnu_afiliado(kwargs, esperado):
    assert cnu.cnu_afiliado(**kwargs) == pytest.approx(esperado, abs=1e-5)


def test_cnu_afiliado_valores_exactos_implementacion():
    """Valores de la implementacion actual, para detectar regresiones."""
    assert cnu.cnu_afiliado(65, agno_vector=2013, agno_actual=2013) == 13.016877
    assert cnu.cnu_afiliado(65, rp=0.0366, agno_actual=2014) == 13.377535
    assert cnu.cnu_afiliado(65, agno_vector=2011, agno_actual=2011) == 12.862231


def test_cnu_conyuge():
    # . cnu_cnyg_s_hi 65 63, agnoa(2011) agnov(2011)   (conymujer=1 por defecto)
    assert cnu.cnu_conyuge(65, 63, agno_vector=2011, agno_actual=2011) == pytest.approx(2.231859, abs=1e-6)


def test_faj_soltero():
    # . cnu_faji 65, rp(.03)   (en 2014)
    assert cnu.faj_afiliado(65, rp=0.03, agno_vector=2013, agno_actual=2014) == pytest.approx(0.066178, abs=1e-6)


def test_faj_con_conyuge():
    # . cnu_faji 65 62, agnov(2013) rp(.03)   (en 2014)
    assert cnu.faj_afiliado(65, 62, agno_vector=2013, rp=0.03, agno_actual=2014) == pytest.approx(0.013094, abs=1e-6)


def test_tablas_2020_explicitas_dan_valores_finitos():
    import math

    for v in (
        cnu.cnu_afiliado(65, tabla="cb2020", rp=0.03, agno_actual=2024),
        cnu.cnu_afiliado(60, mujer=True, tabla="rv2020", rp=0.03, agno_actual=2024),
        cnu.cnu_conyuge(65, 62, tabla="cb2020", tabla_benef="b2020", rp=0.03, agno_actual=2024),
        cnu.cnu_conyuge(60, 65, cot_mujer=True, cony_mujer=False, tabla="rv2020", tabla_benef="cb2020", rp=0.03, agno_actual=2024),
        cnu.cnu_sobrevivencia_conyuge(62, mujer=True, tabla_benef="b2020", rp=0.03, agno_actual=2024),
        cnu.faj_afiliado(65, tabla="cb2020", agno_vector=2013, agno_actual=2024),
    ):
        assert math.isfinite(v) and v > 0
    r = cnu.proyectar_pension(65, 62, saldo=1000.0, tabla="cb2020", tabla_benef="b2020", rp=0.03, agno_actual=2024)
    assert np.all(np.isfinite(r.pension)) and np.all(r.pension > 0)


def test_fsiniestro_resuelve_tablas_2020():
    assert cnu.tabla_mortalidad("rv2009", cnu.ROL_AFILIADO, False, 20240101).nombre == "cnu_tabmor_cb2020h"
    assert cnu.tabla_mortalidad("rv2009", cnu.ROL_AFILIADO, True, 20240101).nombre == "cnu_tabmor_rv2020m"
    assert cnu.tabla_mortalidad("b2006", cnu.ROL_BENEFICIARIO, True, 20240101).nombre == "cnu_tabmor_b2020m"
    assert cnu.tabla_mortalidad("b2006", cnu.ROL_BENEFICIARIO, False, 20240101).nombre == "cnu_tabmor_cb2020h"
    # Lo mismo, de punta a punta: fsiniestro equivale a la tabla 2020 explicita.
    assert cnu.cnu_afiliado(65, fsiniestro=20240101, rp=0.03, agno_actual=2024) == cnu.cnu_afiliado(
        65, tabla="cb2020", rp=0.03, agno_actual=2024
    )
    assert cnu.cnu_afiliado(65, mujer=True, fsiniestro=20240101, rp=0.03, agno_actual=2024) == cnu.cnu_afiliado(
        65, mujer=True, tabla="rv2020", rp=0.03, agno_actual=2024
    )
    assert cnu.cnu_conyuge(65, 62, fsiniestro=20240101, rp=0.03, agno_actual=2024) == cnu.cnu_conyuge(
        65, 62, tabla="cb2020", tabla_benef="b2020", rp=0.03, agno_actual=2024
    )
    assert cnu.cnu_conyuge(65, 62, cony_mujer=False, fsiniestro=20240101, rp=0.03, agno_actual=2024) == cnu.cnu_conyuge(
        65, 62, cony_mujer=False, tabla="cb2020", tabla_benef="cb2020", rp=0.03, agno_actual=2024
    )


def test_fsiniestro_anterior_a_2016_no_cambia():
    # Vigencia 2010-2016: rv2009 / b2006, los mismos defaults historicos (y, sin
    # tasa, el vector del agno del siniestro: 2013).
    assert cnu.cnu_afiliado(65, fsiniestro=20130101, agno_actual=2013) == pytest.approx(13.016877)
    assert cnu.cnu_conyuge(65, 63, fsiniestro=20110301, agno_actual=2011, agno_vector=2011) == pytest.approx(2.231859)
    # Vigencia 2005-2008: rv2004 (mismo valor que pedirla explicitamente).
    assert cnu.cnu_afiliado(65, fsiniestro=20060101, rp=0.03, agno_actual=2013) == cnu.cnu_afiliado(
        65, tabla="rv2004", rp=0.03, agno_actual=2013
    )


def test_describir_muestra_tabla_resuelta():
    d = cnu.describir("soltero sin hijos", "rv2009", rp=0.03, agno_actual=2024, fsiniestro=20240101)
    assert "tabla cb2020h" in d
    d = cnu.describir("soltero sin hijos", "rv2009", rp=0.03, agno_actual=2024, fsiniestro=20240101, mujer=True)
    assert "tabla rv2020m" in d
    d = cnu.describir("conyuge sin hijos", "rv2009", "b2006", agno_actual=2013, fsiniestro=20130101)
    assert "tablas rv2009h b2006m" in d


def test_constantes_articulo_58():
    """Porcentajes del articulo 58 del D.L. N 3.500 y ajuste por pago mensual, como constantes publicas."""
    assert cnu.FRACCION_CONYUGE == 0.6
    assert cnu.FRACCION_CONYUGE_CON_HIJOS == 0.5
    assert cnu.FRACCION_MADRE_PADRE == 0.36
    assert cnu.FRACCION_MADRE_PADRE_CON_HIJOS == 0.30
    assert cnu.FRACCION_HIJO == 0.15
    assert cnu.FRACCION_HIJO_INVALIDO_PARCIAL == 0.11
    assert cnu.FRACCION_PADRES == 0.5
    assert cnu.AJUSTE_MENSUAL == 11 / 24
    for nombre in ("FRACCION_CONYUGE", "FRACCION_CONYUGE_CON_HIJOS", "FRACCION_MADRE_PADRE",
                   "FRACCION_MADRE_PADRE_CON_HIJOS", "FRACCION_HIJO", "FRACCION_HIJO_INVALIDO_PARCIAL",
                   "FRACCION_PADRES", "AJUSTE_MENSUAL"):
        assert nombre in cnu.__all__


def _formula_hijo_anexo7(h, x=None, i=0.03, agno=2026, hijo_mujer=True, cot_mujer=False):
    """Transcripcion directa de las letras 1.d (sin ``x``) y 2.e (con ``x``)
    del Anexo N 7, con tasa constante ``i`` y las tablas vigentes en ``agno``.

    Procedimiento (z = 24, N = z - h periodos, t = 0..23-h):

    1. ``q_h+t`` mejorados a ``agno`` de la tabla de beneficiario del sexo del
       hijo y, para 2.e, ``q_x+t`` de la tabla del afiliado.
    2. ``l_0 = 1``, ``l_t = l_{t-1} (1 - q_{h+t-1})`` (idem ``l^x_t``).
    3. ``v_t = 1 / (1 + i)^t``.
    4. 1.d: ``0,15 [ sum_{t=0}^{23-h} l_t v_t - 11/24 (1 - l_N v_N) ]``.
       2.e: ``0,15 [ sum l_t v_t - sum l_t l^x_t v_t - 11/24 v_N (l^x_N l_N - l_N) ]``.
    """
    n = 24 - h
    qh = cnu.tabla_mortalidad("vigente", cnu.ROL_BENEFICIARIO, hijo_mujer, agno_actual=agno).qx_mejorado(agno, h)
    lh = [1.0]
    for t in range(n):
        lh.append(lh[-1] * (1 - qh[h + t]))
    v = [(1 + i) ** -t for t in range(n + 1)]
    suma = sum(lh[t] * v[t] for t in range(n))
    if x is None:
        return round(0.15 * (suma - 11 / 24 * (1 - lh[n] * v[n])), 6)
    qx = cnu.tabla_mortalidad("vigente", cnu.ROL_AFILIADO, cot_mujer, agno_actual=agno).qx_mejorado(agno, x)
    lx = [1.0]
    for t in range(n):
        lx.append(lx[-1] * (1 - qx[x + t]))
    conjunta = sum(lh[t] * lx[t] * v[t] for t in range(n))
    return round(0.15 * (suma - conjunta - 11 / 24 * v[n] * (lx[n] * lh[n] - lh[n])), 6)


def test_hijo_valores_de_referencia_anexo7():
    """Hijo no invalido de 21 agnos (mujer, b2020m) y afiliado de 65 (cb2020h),
    tasa 3% en 2026: tres periodos (t = 0, 1, 2) y ajuste con N = 3.

    Con q_21..q_23 = 0.00028928, 0.00029567, 0.00029915 (b2020m mejorada a
    2026) resulta l_1..l_3 = 0.99971072, 0.99941513, 0.99911616 y

        1.d: 0,15 [ 1 + 0.99971072/1.03 + 0.99941513/1.03^2
                    - 11/24 (1 - 0.99911616/1.03^3) ] = 0.431006

    Con q_65..q_67 = 0.00794991, 0.00877369, 0.00983352 (cb2020h mejorada a
    2026): l^x_1..l^x_3 = 0.99205009, 0.98334615, 0.97367639 y

        2.e: 0,15 [ 2.912985 - sum l_t l^x_t v_t (= 2.882433)
                    - 11/24 / 1.03^3 (0.97367639 * 0.99911616 - 0.99911616) ] = 0.005165
    """
    assert _formula_hijo_anexo7(21) == 0.431006
    assert cnu.cnu_sobrevivencia_hijo(21, mujer=True, rp=0.03, agno_actual=2026) == 0.431006
    assert _formula_hijo_anexo7(21, x=65) == 0.005165
    assert cnu.cnu_hijo(65, 21, hijo_mujer=True, rp=0.03, agno_actual=2026) == 0.005165
    # Otras edades, contra la misma transcripcion de la formula.
    for h in (0, 5, 10, 17, 23):
        assert cnu.cnu_sobrevivencia_hijo(h, mujer=True, rp=0.03, agno_actual=2026) == _formula_hijo_anexo7(h)
        assert cnu.cnu_hijo(65, h, hijo_mujer=True, rp=0.03, agno_actual=2026) == _formula_hijo_anexo7(h, x=65)
    assert cnu.cnu_hijo(60, 10, cot_mujer=True, hijo_mujer=False, rp=0.03, agno_actual=2026) == _formula_hijo_anexo7(
        10, x=60, hijo_mujer=False, cot_mujer=True
    )


def test_hijo_edad_limite_y_monotonia():
    """Con h >= 24 el CNU es 0 (edad limite z = 24) y decrece con la edad del hijo."""
    assert cnu.EDAD_LIMITE_HIJO == 24 and cnu.EDAD_MINIMA_HIJO == 0
    for h in (24, 25, 40, 110):
        assert cnu.cnu_sobrevivencia_hijo(h, rp=0.03, agno_actual=2026) == 0.0
        assert cnu.cnu_hijo(65, h, rp=0.03, agno_actual=2026) == 0.0
    assert cnu.cnu_sobrevivencia_hijo(23.5, rp=0.03, agno_actual=2026) == 0.0  # edad actuarial 24
    sob = [cnu.cnu_sobrevivencia_hijo(h, rp=0.03, agno_actual=2026) for h in range(0, 25)]
    vej = [cnu.cnu_hijo(65, h, rp=0.03, agno_actual=2026) for h in range(0, 25)]
    assert all(a > b for a, b in zip(sob, sob[1:])) and sob[-1] == 0.0
    assert all(a > b for a, b in zip(vej, vej[1:])) and vej[-1] == 0.0
    # Condicionado al fallecimiento del afiliado, el CNU de vejez es menor que el de sobrevivencia.
    assert all(v < s for v, s in zip(vej[:-1], sob[:-1]))
    # Misma regla de tasa, tabla y edad actuarial que las funciones existentes.
    with pytest.raises(ValueError, match="TITRP"):
        cnu.cnu_hijo(65, 10, agno_actual=2026)
    with pytest.raises(ValueError, match="TITRP"):
        cnu.cnu_sobrevivencia_hijo(10, agno_actual=2026)
    assert cnu.cnu_hijo(65, 10, fsiniestro=20240101, rp=0.03, agno_actual=2026) == cnu.cnu_hijo(
        65, 10, tabla="cb2020", tabla_benef="cb2020", rp=0.03, agno_actual=2026
    )
    assert cnu.cnu_sobrevivencia_hijo(10.5, mujer=True, rp=0.03, agno_actual=2026) == cnu.cnu_sobrevivencia_hijo(
        11, mujer=True, rp=0.03, agno_actual=2026
    )
    d = cnu.describir("hijo no inválido 15%", "vigente", "vigente", rp=0.03, agno_actual=2026, benef_mujer=False)
    assert d == "CNU RP para hijo no inválido 15% (tablas cb2020h cb2020h), tasa 3% en el año 2026"


def _formula_hijo_invalido_anexo7(h, x=None, parcial=False, i=0.03, agno=2026, hijo_mujer=False, cot_mujer=False):
    """Transcripcion directa de las letras 1.e (sin ``x``) y 2.f (con ``x``)
    del Anexo N 7 para hijos invalidos, con tasa constante ``i`` y las tablas
    vigentes en ``agno`` (la del hijo es la de invalidos ``mi``).

    Procedimiento (z = 24, N = z - hi, w hasta los 110 agnos, t = 0..w):

    1. ``q_hi+t`` mejorados a ``agno`` de la tabla ``mi`` del sexo del hijo
       (``q = 1`` mas alla de la tabla) y, para 2.f, ``q_x+t`` de la del afiliado.
    2. ``l_0 = 1``, ``l_t = l_{t-1} (1 - q_{hi+t-1})`` (idem ``l^x_t``).
    3. ``v_t = 1 / (1 + i)^t``; en 2.f cada termino lleva ``(1 - l^x_t)``.
    4. Total:   1.e ``0,15 [ sum_{t=0}^{w} l_t v_t - 11/24 ]``;
                2.f ``0,15 sum_{t=0}^{w} l_t (1 - l^x_t) v_t`` (sin ajuste).
       Parcial, hi < 24:
                1.e ``0,15 [ sum_{t<N} l_t v_t - 11/24 (1 - l_N v_N) ]
                     + 0,11 [ sum_{t>=N} l_t v_t - 11/24 l_N v_N ]``;
                2.f ``0,15 sum_{t<N} l_t (1 - l^x_t) v_t + 0,11 sum_{t>=N} l_t (1 - l^x_t) v_t
                     + 0,04 * 11/24 l_N v_N (1 - l^x_N)``.
       Parcial, hi >= 24: la formula del total con 0,11 en vez de 0,15.
    """
    w = 110 - h + (0 if x is None else 1)
    q = np.concatenate([cnu.tabla_mortalidad("vigente", cnu.ROL_INVALIDO, hijo_mujer, agno_actual=agno)
                        .qx_mejorado(agno, h), np.ones(200)])
    lh = [1.0]
    for t in range(w + 1):
        lh.append(lh[-1] * (1 - q[h + t]))
    v = [(1 + i) ** -t for t in range(w + 2)]
    n = 24 - h
    if x is None:
        vit = sum(lh[t] * v[t] for t in range(w + 1)) - 11 / 24
        if not parcial:
            return round(0.15 * vit, 6)
        if h >= 24:
            return round(0.11 * vit, 6)
        temporal = sum(lh[t] * v[t] for t in range(n)) - 11 / 24 * (1 - lh[n] * v[n])
        diferida = sum(lh[t] * v[t] for t in range(n, w + 1)) - 11 / 24 * lh[n] * v[n]
        return round(0.15 * temporal + 0.11 * diferida, 6)
    qx = np.concatenate([cnu.tabla_mortalidad("vigente", cnu.ROL_AFILIADO, cot_mujer, agno_actual=agno)
                         .qx_mejorado(agno, x), np.ones(300)])
    lx = [1.0]
    for t in range(w + 1):
        lx.append(lx[-1] * (1 - qx[x + t]))
    termino = [lh[t] * (1 - lx[t]) * v[t] for t in range(w + 1)]
    if not parcial:
        return round(0.15 * sum(termino), 6)
    if h >= 24:
        return round(0.11 * sum(termino), 6)
    ajuste = 11 / 24 * lh[n] * v[n] * (1 - lx[n])
    return round(0.15 * sum(termino[:n]) + 0.11 * sum(termino[n:]) + 0.04 * ajuste, 6)


def test_hijo_invalido_valores_de_referencia_anexo7():
    """Hijo invalido de 21 agnos (mujer, mi2020m) y afiliado de 65 (cb2020h),
    tasa 3% en 2026; N = 3 periodos hasta los 24.

    Con q_21..q_23 = 0.00321774, 0.00328866, 0.00332736 (mi2020m mejorada a
    2026) resulta l_1..l_3 = 0.99678226, 0.99350435, 0.99019843, v_3 = 0.91514166,
    y sumando la vitalicia hasta los 110:

        1.e total:   0,15 [ 26.721846 - 11/24 ] = 0,15 * 26.263401 = 3.939510
        1.e parcial: temporal = 1 + 0.99678226/1.03 + 0.99350435/1.03^2
                                - 11/24 (1 - 0.99019843 * 0.91514166) = 2.861218
                     diferida = sum_{t>=3} l_t v_t - 11/24 * 0.99019843 * 0.91514166 = 23.402183
                     0,15 * 2.861218 + 0,11 * 23.402183 = 3.003423

    Con l^x_1..l^x_3 = 0.99205009, 0.98334615, 0.97367639 (cb2020h a 2026):

        2.f total:   0,15 * 11.436617 = 1.715493
        2.f parcial: 0,15 * 0.023289 + 0,11 * 11.413327
                     + 0,04 * 11/24 * 0.99019843 * 0.91514166 * (1 - 0.97367639) = 1.259397

    Hijo invalido total de 30 agnos (hombre, mi2020h) con afiliado de 65:
    2.f total 0,15 * 8.383032 = 1.257455 (positivo: no hay edad limite).
    """
    assert _formula_hijo_invalido_anexo7(21, hijo_mujer=True) == 3.939510
    assert cnu.cnu_sobrevivencia_hijo_invalido(21, mujer=True, rp=0.03, agno_actual=2026) == 3.939510
    assert _formula_hijo_invalido_anexo7(21, parcial=True, hijo_mujer=True) == 3.003423
    assert cnu.cnu_sobrevivencia_hijo_invalido(21, mujer=True, parcial=True, rp=0.03, agno_actual=2026) == 3.003423
    assert _formula_hijo_invalido_anexo7(21, x=65, hijo_mujer=True) == 1.715493
    assert cnu.cnu_hijo_invalido(65, 21, hijo_mujer=True, rp=0.03, agno_actual=2026) == 1.715493
    assert _formula_hijo_invalido_anexo7(21, x=65, parcial=True, hijo_mujer=True) == 1.259397
    assert cnu.cnu_hijo_invalido(65, 21, hijo_mujer=True, parcial=True, rp=0.03, agno_actual=2026) == 1.259397
    assert _formula_hijo_invalido_anexo7(30, x=65) == 1.257455
    assert cnu.cnu_hijo_invalido(65, 30, rp=0.03, agno_actual=2026) == 1.257455
    # Otras edades y grados, contra la misma transcripcion de la formula.
    for h in (0, 10, 23, 24, 30, 60):
        for parcial in (False, True):
            assert cnu.cnu_sobrevivencia_hijo_invalido(h, parcial=parcial, rp=0.03, agno_actual=2026) == (
                _formula_hijo_invalido_anexo7(h, parcial=parcial)
            )
            assert cnu.cnu_hijo_invalido(65, h, parcial=parcial, rp=0.03, agno_actual=2026) == (
                _formula_hijo_invalido_anexo7(h, x=65, parcial=parcial)
            )
    assert cnu.cnu_hijo_invalido(60, 10, cot_mujer=True, hijo_mujer=True, parcial=True, rp=0.03, agno_actual=2026) == (
        _formula_hijo_invalido_anexo7(10, x=60, parcial=True, hijo_mujer=True, cot_mujer=True)
    )


def test_hijo_invalido_sin_edad_limite_y_tramos():
    """El hijo invalido total no depende de la edad limite de 24 (un hijo de 30
    tiene CNU positivo); el parcial vale 15% hasta los 24 y 11% despues."""
    for h in (24, 30, 60):
        assert cnu.cnu_hijo_invalido(65, h, rp=0.03, agno_actual=2026) > 0
        assert cnu.cnu_sobrevivencia_hijo_invalido(h, rp=0.03, agno_actual=2026) > 0
        # Con h >= 24 el parcial es el 11% de la misma anualidad: 11/15 del total.
        assert cnu.cnu_hijo_invalido(65, h, parcial=True, rp=0.03, agno_actual=2026) == pytest.approx(
            cnu.cnu_hijo_invalido(65, h, rp=0.03, agno_actual=2026) * 11 / 15, abs=1e-6
        )
        assert cnu.cnu_sobrevivencia_hijo_invalido(h, parcial=True, rp=0.03, agno_actual=2026) == pytest.approx(
            cnu.cnu_sobrevivencia_hijo_invalido(h, rp=0.03, agno_actual=2026) * 11 / 15, abs=1e-6
        )
    # Con h < 24 el parcial esta entre el 11% y el 15% de la anualidad completa.
    for h in (0, 10, 23):
        total = cnu.cnu_sobrevivencia_hijo_invalido(h, rp=0.03, agno_actual=2026)
        parcial = cnu.cnu_sobrevivencia_hijo_invalido(h, parcial=True, rp=0.03, agno_actual=2026)
        assert total * 11 / 15 < parcial < total
        total = cnu.cnu_hijo_invalido(65, h, rp=0.03, agno_actual=2026)
        parcial = cnu.cnu_hijo_invalido(65, h, parcial=True, rp=0.03, agno_actual=2026)
        assert total * 11 / 15 < parcial < total
    # Decrece con la edad del hijo, sin llegar a 0; y condicionado al
    # fallecimiento del afiliado es menor que el de sobrevivencia.
    sob = [cnu.cnu_sobrevivencia_hijo_invalido(h, rp=0.03, agno_actual=2026) for h in range(0, 61, 5)]
    vej = [cnu.cnu_hijo_invalido(65, h, rp=0.03, agno_actual=2026) for h in range(0, 61, 5)]
    assert all(a > b > 0 for a, b in zip(sob, sob[1:]))
    assert all(v < s for v, s in zip(vej, sob))
    # Tabla de invalidos del sexo del hijo: distinta de la del hijo no invalido.
    assert cnu.cnu_sobrevivencia_hijo_invalido(10, rp=0.03, agno_actual=2026) == cnu.cnu_sobrevivencia_hijo_invalido(
        10, tabla_benef="mi2020", rp=0.03, agno_actual=2026
    )
    assert cnu.cnu_sobrevivencia_hijo_invalido(10, rp=0.03, agno_actual=2026) != cnu.cnu_sobrevivencia_hijo_invalido(
        10, tabla_benef="cb2020", rp=0.03, agno_actual=2026
    )
    # Misma regla de tasa, tabla por fecha y edad actuarial que las funciones existentes.
    with pytest.raises(ValueError, match="TITRP"):
        cnu.cnu_hijo_invalido(65, 10, agno_actual=2026)
    with pytest.raises(ValueError, match="TITRP"):
        cnu.cnu_sobrevivencia_hijo_invalido(10, agno_actual=2026)
    assert cnu.cnu_hijo_invalido(65, 10, fsiniestro=20130101, rp=0.03, agno_actual=2026) == cnu.cnu_hijo_invalido(
        65, 10, tabla="rv2009", tabla_benef="mi2006", rp=0.03, agno_actual=2026
    )
    assert cnu.cnu_sobrevivencia_hijo_invalido(23.5, parcial=True, rp=0.03, agno_actual=2026) == (
        cnu.cnu_sobrevivencia_hijo_invalido(24, parcial=True, rp=0.03, agno_actual=2026)
    )
    d = cnu.describir("hijo inválido parcial 15%/11%", "vigente", "vigente", rp=0.03, agno_actual=2026,
                      benef_mujer=True, rol_benef=cnu.ROL_INVALIDO)
    assert d == "CNU RP para hijo inválido parcial 15%/11% (tablas cb2020h mi2020m), tasa 3% en el año 2026"
    for nombre in ("cnu_hijo_invalido", "cnu_sobrevivencia_hijo_invalido", "cnu_hijo_invalido_vec",
                   "cnu_sobrevivencia_hijo_invalido_vec"):
        assert nombre in cnu.__all__


def _formula_conyuge_con_hijos_anexo7(y, h, x=None, i=0.03, agno=2026, cony_mujer=True, cot_mujer=False,
                                      hijo_invalido=False, p_con=0.5, p_sin=0.6):
    """Transcripcion directa de las letras 1.b y 1.c (sin ``x``) y 2.c y 2.d
    (con ``x``) del Anexo N 7 para el conyuge con hijos, con tasa constante
    ``i`` y las tablas vigentes en ``agno``. Con ``p_con = 0,30`` y ``p_sin =
    0,36`` es la transcripcion de las letras 1.h, 1.i y 1.j (sin ``x``) y
    2.i, 2.j y 2.k (con ``x``) de la madre o el padre de hijos no
    matrimoniales, cuya estructura es la misma (``u`` en lugar de ``y``, y el
    0,1 pasa a ser ``p_sin - p_con = 0,06``); ``h = None`` es la letra sin
    hijos con derecho (``p_sin`` vitalicio).

    Procedimiento (z = 24, N = z - h = y' - y, w hasta los 110 agnos):

    1. ``q_y+t`` mejorados a ``agno`` de la tabla de beneficiario del sexo del
       conyuge (``q = 1`` mas alla de la tabla) y, para 2.c y 2.d, ``q_x+t`` de
       la del afiliado.
    2. ``l_0 = 1``, ``l_t = l_{t-1} (1 - q_{y+t-1})`` (idem ``l^x_t``).
    3. ``v_t = 1 / (1 + i)^t``; en 2.c y 2.d cada termino lleva ``(1 - l^x_t)``.
    4. 1.b: ``0,5 [ sum_{t=0}^{w} l_t v_t - 11/24 ]
             + 0,1 [ sum_{t=0}^{w} l_{N+t} v_{N+t} - 11/24 l_N v_N ]``;
       1.c: ``0,5 [ sum_{t=0}^{w} l_t v_t - 11/24 ]``;
       2.c: ``0,5 sum_{t=0}^{w} l_t (1 - l^x_t) v_t
             + 0,1 sum_{t=0}^{w} l_{N+t} (1 - l^x_{N+t}) v_{N+t}
             - 0,1 * 11/24 l_N v_N (1 - l^x_N)``;
       2.d: ``0,5 sum_{t=0}^{w} l_t (1 - l^x_t) v_t``.
    """
    w = 110 - y + (0 if x is None else 1)
    q = np.concatenate([cnu.tabla_mortalidad("vigente", cnu.ROL_BENEFICIARIO, cony_mujer, agno_actual=agno)
                        .qx_mejorado(agno, y), np.ones(300)])
    ly = [1.0]
    for t in range(w + 40):
        ly.append(ly[-1] * (1 - q[y + t]))
    v = [(1 + i) ** -t for t in range(w + 41)]
    n = 24 - (0 if h is None else h)
    if x is None:
        vitalicia = sum(ly[t] * v[t] for t in range(w + 1)) - 11 / 24
        if hijo_invalido:
            return round(p_con * vitalicia, 6)
        if h is None:
            return round(p_sin * vitalicia, 6)
        diferida = sum(ly[n + t] * v[n + t] for t in range(w + 1 - n)) - 11 / 24 * ly[n] * v[n]
        return round(p_con * vitalicia + (p_sin - p_con) * diferida, 6)
    qx = np.concatenate([cnu.tabla_mortalidad("vigente", cnu.ROL_AFILIADO, cot_mujer, agno_actual=agno)
                         .qx_mejorado(agno, x), np.ones(300)])
    lx = [1.0]
    for t in range(w + 40):
        lx.append(lx[-1] * (1 - qx[x + t]))
    termino = [ly[t] * (1 - lx[t]) * v[t] for t in range(w + 41)]
    vitalicia = sum(termino[: w + 1])
    if hijo_invalido:
        return round(p_con * vitalicia, 6)
    if h is None:
        return round(p_sin * vitalicia, 6)
    diferida = sum(termino[n: w + 1])
    return round(p_con * vitalicia + (p_sin - p_con) * (diferida - 11 / 24 * ly[n] * v[n] * (1 - lx[n])), 6)


def test_conyuge_con_hijos_valores_de_referencia_anexo7():
    """Conyuge de 63 agnos (mujer, b2020m) con hijo menor de 21 y afiliado de
    65 (cb2020h), tasa 3% en 2026: y' = 66, N = 3 periodos hasta los 24 del
    hijo.

    Con q_63..q_65 = 0.00475078, 0.00525371, 0.00580256 (b2020m mejorada a
    2026) resulta l_1..l_3 = 0.99524922, 0.99002047, 0.98427582,
    v_3 = 0.91514166 y l_3 v_3 = 0.90075181; sumando hasta los 110:

        1.b: 0,5 [ 18.248965 - 11/24 ] + 0,1 [ 15.349515 - 11/24 * 0.90075181 ]
             = 0,5 * 17.790632 + 0,1 * 14.936670 = 10.388983
        1.c: 0,5 * 17.790632 = 8.895316

    Con l^x_1..l^x_3 = 0.99205009, 0.98334615, 0.97367639 (cb2020h a 2026):

        2.c: 0,5 * 4.155463 + 0,1 * 4.132240
             - 0,1 * 11/24 * 0.90075181 * (1 - 0.97367639) = 2.489869
        2.d: 0,5 * 4.155463 = 2.077732

    Equivalen a los dos tramos 0,5 * temporal + 0,6 * (vitalicia - temporal),
    con temporal = 2.853962 en 1.b: 0,5 * 2.853962 + 0,6 * 14.936670 = 10.388983.
    """
    assert _formula_conyuge_con_hijos_anexo7(63, 21) == 10.388983
    assert cnu.cnu_sobrevivencia_conyuge_con_hijos(63, 21, mujer=True, rp=0.03, agno_actual=2026) == 10.388983
    assert _formula_conyuge_con_hijos_anexo7(63, 21, hijo_invalido=True) == 8.895316
    assert cnu.cnu_sobrevivencia_conyuge_con_hijos(63, 21, mujer=True, hijo_invalido=True, rp=0.03,
                                                   agno_actual=2026) == 8.895316
    assert _formula_conyuge_con_hijos_anexo7(63, 21, x=65) == 2.489869
    assert cnu.cnu_conyuge_con_hijos(65, 63, 21, rp=0.03, agno_actual=2026) == 2.489869
    assert _formula_conyuge_con_hijos_anexo7(63, 21, x=65, hijo_invalido=True) == 2.077732
    assert cnu.cnu_conyuge_con_hijos(65, 63, 21, hijo_invalido=True, rp=0.03, agno_actual=2026) == 2.077732
    # Otras edades, contra la misma transcripcion de la formula (incluido el
    # conyuge de 90 con un hijo de 0, cuyo tramo al 60% queda fuera de la tabla).
    for y, h in ((63, 0), (63, 10), (63, 23), (40, 3), (30, 17), (90, 0)):
        for hijo_invalido in (False, True):
            assert cnu.cnu_sobrevivencia_conyuge_con_hijos(y, h, mujer=True, hijo_invalido=hijo_invalido, rp=0.03,
                                                           agno_actual=2026) == (
                _formula_conyuge_con_hijos_anexo7(y, h, hijo_invalido=hijo_invalido)
            )
            assert cnu.cnu_conyuge_con_hijos(65, y, h, hijo_invalido=hijo_invalido, rp=0.03, agno_actual=2026) == (
                _formula_conyuge_con_hijos_anexo7(y, h, x=65, hijo_invalido=hijo_invalido)
            )
    assert cnu.cnu_conyuge_con_hijos(60, 62, 10, cot_mujer=True, cony_mujer=False, rp=0.03, agno_actual=2026) == (
        _formula_conyuge_con_hijos_anexo7(62, 10, x=60, cony_mujer=False, cot_mujer=True)
    )


def test_conyuge_con_hijos_tramos_y_conviviente():
    """Con el hijo menor de 24 o mas el resultado es exactamente el del conyuge
    sin hijos; con menos, es menor y crece con la edad del hijo; con hijo
    invalido es 50% vitalicio; el conviviente civil vale lo mismo que el conyuge."""
    sin_hijos = cnu.cnu_conyuge(65, 63, rp=0.03, agno_actual=2026)
    sob_sin_hijos = cnu.cnu_sobrevivencia_conyuge(63, mujer=True, rp=0.03, agno_actual=2026)
    for h in (24, 23.5, 30, 110):
        assert cnu.cnu_conyuge_con_hijos(65, 63, h, rp=0.03, agno_actual=2026) == sin_hijos
        assert cnu.cnu_sobrevivencia_conyuge_con_hijos(63, h, mujer=True, rp=0.03, agno_actual=2026) == sob_sin_hijos
    vej = [cnu.cnu_conyuge_con_hijos(65, 63, h, rp=0.03, agno_actual=2026) for h in range(0, 25)]
    sob = [cnu.cnu_sobrevivencia_conyuge_con_hijos(63, h, mujer=True, rp=0.03, agno_actual=2026) for h in range(0, 25)]
    assert all(v < sin_hijos for v in vej[:-1]) and all(s < sob_sin_hijos for s in sob[:-1])
    assert all(a < b for a, b in zip(vej, vej[1:])) and all(a < b for a, b in zip(sob, sob[1:]))
    assert all(v < s for v, s in zip(vej, sob))
    # Con algun hijo invalido: 50% vitalicio (5/6 del 60% sin hijos), sin que h intervenga.
    for h in (0, 10, 30):
        assert cnu.cnu_conyuge_con_hijos(65, 63, h, hijo_invalido=True, rp=0.03, agno_actual=2026) == pytest.approx(
            sin_hijos * 5 / 6, abs=1e-6
        )
        assert cnu.cnu_sobrevivencia_conyuge_con_hijos(63, h, mujer=True, hijo_invalido=True, rp=0.03,
                                                       agno_actual=2026) == pytest.approx(sob_sin_hijos * 5 / 6, abs=1e-6)
    assert all(cnu.cnu_conyuge_con_hijos(65, 63, h, hijo_invalido=True, rp=0.03, agno_actual=2026) <= v
               for h, v in enumerate(vej))
    # Conviviente civil: misma formula, mismo valor (escalar y vectorial).
    assert cnu.cnu_conyuge(65, 63, conviviente=True, rp=0.03, agno_actual=2026) == sin_hijos
    assert cnu.cnu_sobrevivencia_conyuge(63, mujer=True, conviviente=True, rp=0.03, agno_actual=2026) == sob_sin_hijos
    assert cnu.cnu_conyuge_con_hijos(65, 63, 10, conviviente=True, rp=0.03, agno_actual=2026) == vej[10]
    assert cnu.cnu_sobrevivencia_conyuge_con_hijos(63, 10, mujer=True, conviviente=True, rp=0.03,
                                                   agno_actual=2026) == sob[10]
    np.testing.assert_array_equal(
        cnu.cnu_conyuge_vec([65, 65], [63, 63], cony_mujer=True, conviviente=[True, False], rp=0.03, agno_actual=2026),
        [sin_hijos, sin_hijos],
    )
    np.testing.assert_array_equal(
        cnu.cnu_sobrevivencia_conyuge_con_hijos_vec([63, 63], [10, 10], mujer=True, conviviente=[True, False],
                                                    rp=0.03, agno_actual=2026),
        [sob[10], sob[10]],
    )
    # Misma regla de tasa, tabla por fecha y edad actuarial que las funciones existentes.
    with pytest.raises(ValueError, match="TITRP"):
        cnu.cnu_conyuge_con_hijos(65, 63, 10, agno_actual=2026)
    with pytest.raises(ValueError, match="TITRP"):
        cnu.cnu_sobrevivencia_conyuge_con_hijos(63, 10, agno_actual=2026)
    assert cnu.cnu_conyuge_con_hijos(65, 63, 10, fsiniestro=20130101, rp=0.03, agno_actual=2026) == (
        cnu.cnu_conyuge_con_hijos(65, 63, 10, tabla="rv2009", tabla_benef="b2006", rp=0.03, agno_actual=2026)
    )
    assert cnu.cnu_sobrevivencia_conyuge_con_hijos(62.5, 9.5, mujer=True, rp=0.03, agno_actual=2026) == (
        cnu.cnu_sobrevivencia_conyuge_con_hijos(63, 10, mujer=True, rp=0.03, agno_actual=2026)
    )
    d = cnu.describir("conviviente civil con hijos 50%/60%", "vigente", "vigente", rp=0.03, agno_actual=2026)
    assert d == "CNU RP para conviviente civil con hijos 50%/60% (tablas cb2020h b2020m), tasa 3% en el año 2026"
    for nombre in ("cnu_conyuge_con_hijos", "cnu_sobrevivencia_conyuge_con_hijos", "cnu_conyuge_con_hijos_vec",
                   "cnu_sobrevivencia_conyuge_con_hijos_vec"):
        assert nombre in cnu.__all__


def test_madre_padre_valores_de_referencia_anexo7():
    """Madre de hijos no matrimoniales de 45 agnos (b2020m) con hijo menor de
    21 y afiliado de 50 (cb2020h), tasa 3% en 2026: u' = 48, N = 3 periodos
    hasta los 24 del hijo. Misma estructura que el conyuge con hijos, con
    30%/36% en lugar de 50%/60%.

    Con q_45..q_47 = 0.00111678, 0.00119909, 0.00127580 (b2020m mejorada a
    2026) resulta l_1..l_3 = 0.99888322, 0.99768547, 0.99641262,
    v_3 = 0.91514166 y l_3 v_3 = 0.91185870; sumando hasta los 110:

        1.h: 0,36 [ 24.674243 - 11/24 ] = 0,36 * 24.215910 = 8.717728
        1.i: 0,30 * 24.215910 + 0,06 [ 21.764040 - 11/24 * 0.91185870 ]
             = 0,30 * 24.215910 + 0,06 * 21.346104 = 8.545539
        1.j: 0,30 * 24.215910 = 7.264773

    Con l^x_1..l^x_3 = 0.99768479, 0.99525956, 0.99274661 (cb2020h a 2026):

        2.i: 0,36 * 3.807863 = 1.370831
        2.j: 0,30 * 3.807863 + 0,06 * 3.801160
             - 0,06 * 11/24 * 0.91185870 * (1 - 0.99274661) = 1.370247
        2.k: 0,30 * 3.807863 = 1.142359
    """
    mp = dict(p_con=0.30, p_sin=0.36)
    assert _formula_conyuge_con_hijos_anexo7(45, None, **mp) == 8.717728
    assert cnu.cnu_sobrevivencia_madre_padre(45, rp=0.03, agno_actual=2026) == 8.717728
    assert _formula_conyuge_con_hijos_anexo7(45, 21, **mp) == 8.545539
    assert cnu.cnu_sobrevivencia_madre_padre(45, 21, rp=0.03, agno_actual=2026) == 8.545539
    assert _formula_conyuge_con_hijos_anexo7(45, 21, hijo_invalido=True, **mp) == 7.264773
    assert cnu.cnu_sobrevivencia_madre_padre(45, 21, hijo_invalido=True, rp=0.03, agno_actual=2026) == 7.264773
    assert _formula_conyuge_con_hijos_anexo7(45, None, x=50, **mp) == 1.370831
    assert cnu.cnu_madre_padre(50, 45, rp=0.03, agno_actual=2026) == 1.370831
    assert _formula_conyuge_con_hijos_anexo7(45, 21, x=50, **mp) == 1.370247
    assert cnu.cnu_madre_padre(50, 45, 21, rp=0.03, agno_actual=2026) == 1.370247
    assert _formula_conyuge_con_hijos_anexo7(45, 21, x=50, hijo_invalido=True, **mp) == 1.142359
    assert cnu.cnu_madre_padre(50, 45, 21, hijo_invalido=True, rp=0.03, agno_actual=2026) == 1.142359
    # Otras edades y el padre (tabla de hombre), contra la misma transcripcion.
    for u, h in ((45, 0), (45, 10), (45, 23), (30, 3), (60, 17), (90, 0)):
        for hijo_invalido in (False, True):
            assert cnu.cnu_sobrevivencia_madre_padre(u, h, hijo_invalido=hijo_invalido, rp=0.03, agno_actual=2026) == (
                _formula_conyuge_con_hijos_anexo7(u, h, hijo_invalido=hijo_invalido, **mp)
            )
            assert cnu.cnu_madre_padre(50, u, h, hijo_invalido=hijo_invalido, rp=0.03, agno_actual=2026) == (
                _formula_conyuge_con_hijos_anexo7(u, h, x=50, hijo_invalido=hijo_invalido, **mp)
            )
    assert cnu.cnu_madre_padre(48, 52, 10, cot_mujer=True, madre=False, rp=0.03, agno_actual=2026) == (
        _formula_conyuge_con_hijos_anexo7(52, 10, x=48, cony_mujer=False, cot_mujer=True, **mp)
    )
    assert cnu.cnu_sobrevivencia_madre_padre(52, madre=False, rp=0.03, agno_actual=2026) == (
        _formula_conyuge_con_hijos_anexo7(52, None, cony_mujer=False, **mp)
    )


def test_madre_padre_tramos():
    """Sin hijos con derecho (h None, nan o 24 o mas) es 36% vitalicio, igual a
    0,6 veces el conyuge sin hijos; con hijos es menor y crece con la edad del
    hijo; con hijo invalido es 30% vitalicio (5/6 del 36%)."""
    sin_hijos = cnu.cnu_madre_padre(50, 45, rp=0.03, agno_actual=2026)
    sob_sin_hijos = cnu.cnu_sobrevivencia_madre_padre(45, rp=0.03, agno_actual=2026)
    assert sin_hijos == pytest.approx(0.6 * cnu.cnu_conyuge(50, 45, rp=0.03, agno_actual=2026), abs=1e-6)
    assert sob_sin_hijos == pytest.approx(0.6 * cnu.cnu_sobrevivencia_conyuge(45, mujer=True, rp=0.03, agno_actual=2026),
                                          abs=1e-6)
    for h in (None, float("nan"), 24, 23.5, 30, 110):
        assert cnu.cnu_madre_padre(50, 45, h, rp=0.03, agno_actual=2026) == sin_hijos
        assert cnu.cnu_sobrevivencia_madre_padre(45, h, rp=0.03, agno_actual=2026) == sob_sin_hijos
    vej = [cnu.cnu_madre_padre(50, 45, h, rp=0.03, agno_actual=2026) for h in range(0, 25)]
    sob = [cnu.cnu_sobrevivencia_madre_padre(45, h, rp=0.03, agno_actual=2026) for h in range(0, 25)]
    assert all(v < sin_hijos for v in vej[:-1]) and all(s < sob_sin_hijos for s in sob[:-1])
    assert all(a < b for a, b in zip(vej, vej[1:])) and all(a < b for a, b in zip(sob, sob[1:]))
    assert all(v < s for v, s in zip(vej, sob))
    for h in (None, 0, 10, 30):
        assert cnu.cnu_madre_padre(50, 45, h, hijo_invalido=True, rp=0.03, agno_actual=2026) == pytest.approx(
            sin_hijos * 5 / 6, abs=1e-6
        )
        assert cnu.cnu_sobrevivencia_madre_padre(45, h, hijo_invalido=True, rp=0.03, agno_actual=2026) == pytest.approx(
            sob_sin_hijos * 5 / 6, abs=1e-6
        )
    # Madre o padre de 90 con hijo de 0: el tramo al 36% queda fuera de la tabla, 30% vitalicio.
    assert cnu.cnu_sobrevivencia_madre_padre(90, 0, rp=0.03, agno_actual=2026) == (
        cnu.cnu_sobrevivencia_madre_padre(90, 0, hijo_invalido=True, rp=0.03, agno_actual=2026)
    )
    # Misma regla de tasa, tabla por fecha y edad actuarial que las funciones existentes.
    with pytest.raises(ValueError, match="TITRP"):
        cnu.cnu_madre_padre(50, 45, 10, agno_actual=2026)
    with pytest.raises(ValueError, match="TITRP"):
        cnu.cnu_sobrevivencia_madre_padre(45, agno_actual=2026)
    assert cnu.cnu_madre_padre(50, 45, 10, fsiniestro=20130101, rp=0.03, agno_actual=2026) == (
        cnu.cnu_madre_padre(50, 45, 10, tabla="rv2009", tabla_benef="b2006", rp=0.03, agno_actual=2026)
    )
    assert cnu.cnu_sobrevivencia_madre_padre(44.5, 9.5, rp=0.03, agno_actual=2026) == (
        cnu.cnu_sobrevivencia_madre_padre(45, 10, rp=0.03, agno_actual=2026)
    )
    d = cnu.describir("madre no matrimonial con hijos 30%/36%", "vigente", "vigente", rp=0.03, agno_actual=2026)
    assert d == "CNU RP para madre no matrimonial con hijos 30%/36% (tablas cb2020h b2020m), tasa 3% en el año 2026"
    for nombre in ("cnu_madre_padre", "cnu_sobrevivencia_madre_padre", "cnu_madre_padre_vec",
                   "cnu_sobrevivencia_madre_padre_vec", "FRACCION_MADRE_PADRE", "FRACCION_MADRE_PADRE_CON_HIJOS"):
        assert nombre in cnu.__all__


def test_padres_valores_de_referencia_anexo7():
    """Madre del afiliado de 88 agnos (b2020m) y afiliado de 65 (cb2020h),
    tasa 3% en 2026. Misma estructura que el conyuge sin hijos, al 50%.

    Con q_88..q_90 = 0.07416447, 0.08220607, 0.09112692 (b2020m mejorada a
    2026) resulta l_1..l_3 = 0.92583553, 0.84972623, 0.77229330; sumando
    hasta los 110:

        1.k: 0,5 [ 6.636411 - 11/24 ] = 3.089039
        2.l: 0,5 * 0.322842 = 0.161421   (terminos con (1 - l^x_t), cb2020h a 2026)

    Cada padre se calcula por separado; ambos padres son la suma de dos
    llamadas (madre con tabla de mujer y padre con tabla de hombre).
    """
    assert _formula_conyuge_con_hijos_anexo7(88, None, p_con=0.5, p_sin=0.5) == 3.089039
    assert cnu.cnu_sobrevivencia_padres(88, rp=0.03, agno_actual=2026) == 3.089039
    assert _formula_conyuge_con_hijos_anexo7(88, None, x=65, p_con=0.5, p_sin=0.5) == 0.161421
    assert cnu.cnu_padres(65, 88, rp=0.03, agno_actual=2026) == 0.161421
    for m, madre in ((88, False), (70, True), (70, False), (95, True), (40, False)):
        assert cnu.cnu_sobrevivencia_padres(m, madre, rp=0.03, agno_actual=2026) == (
            _formula_conyuge_con_hijos_anexo7(m, None, cony_mujer=madre, p_con=0.5, p_sin=0.5)
        )
        assert cnu.cnu_padres(65, m, madre=madre, rp=0.03, agno_actual=2026) == (
            _formula_conyuge_con_hijos_anexo7(m, None, x=65, cony_mujer=madre, p_con=0.5, p_sin=0.5)
        )
    assert cnu.cnu_padres(60, 85, cot_mujer=True, madre=False, rp=0.03, agno_actual=2026) == (
        _formula_conyuge_con_hijos_anexo7(85, None, x=60, cony_mujer=False, cot_mujer=True, p_con=0.5, p_sin=0.5)
    )
    # 50% vitalicio: 5/6 del conyuge sin hijos de la misma edad y sexo.
    assert cnu.cnu_padres(65, 88, rp=0.03, agno_actual=2026) == pytest.approx(
        cnu.cnu_conyuge(65, 88, rp=0.03, agno_actual=2026) * 5 / 6, abs=1e-6
    )
    assert cnu.cnu_sobrevivencia_padres(88, madre=False, rp=0.03, agno_actual=2026) == pytest.approx(
        cnu.cnu_sobrevivencia_conyuge(88, rp=0.03, agno_actual=2026) * 5 / 6, abs=1e-6
    )
    # Ambos padres: dos llamadas, con la tabla del sexo de cada uno; el padre
    # (cb2020h) vale menos que la madre (b2020m) a igual edad.
    madre, padre = (cnu.cnu_padres(65, 88, madre=m, rp=0.03, agno_actual=2026) for m in (True, False))
    assert 0 < padre < madre and madre + padre == pytest.approx(0.161421 + padre)
    # Misma regla de tasa, tabla por fecha y edad actuarial que las funciones existentes.
    with pytest.raises(ValueError, match="TITRP"):
        cnu.cnu_padres(65, 88, agno_actual=2026)
    with pytest.raises(ValueError, match="TITRP"):
        cnu.cnu_sobrevivencia_padres(88, agno_actual=2026)
    assert cnu.cnu_padres(65, 88, fsiniestro=20130101, rp=0.03, agno_actual=2026) == (
        cnu.cnu_padres(65, 88, tabla="rv2009", tabla_benef="b2006", rp=0.03, agno_actual=2026)
    )
    assert cnu.cnu_sobrevivencia_padres(87.5, rp=0.03, agno_actual=2026) == cnu.cnu_sobrevivencia_padres(
        88, rp=0.03, agno_actual=2026
    )
    d = cnu.describir("padre del afiliado 50%", "vigente", "vigente", rp=0.03, agno_actual=2026, benef_mujer=False)
    assert d == "CNU RP para padre del afiliado 50% (tablas cb2020h cb2020h), tasa 3% en el año 2026"
    for nombre in ("cnu_padres", "cnu_sobrevivencia_padres", "cnu_padres_vec", "cnu_sobrevivencia_padres_vec",
                   "FRACCION_PADRES"):
        assert nombre in cnu.__all__

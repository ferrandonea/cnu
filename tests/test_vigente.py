"""Default ``"vigente"``: tabla segun rol, sexo y fecha (fin de agno sin fsiniestro)."""

import numpy as np
import pytest

import cnu
from cnu import tablas
from cnu.cli import construir_parser, main


def _nombre(tabla, rol, mujer, **kw):
    return cnu.tabla_mortalidad(tabla, rol, mujer, **kw).nombre


def test_defaults_son_vigente():
    assert cnu.TABLA_AFILIADO == cnu.TABLA_BENEFICIARIO == cnu.TABLA_VIGENTE == "vigente"


def test_vigente_2026_selecciona_tm2020():
    assert _nombre("vigente", cnu.ROL_AFILIADO, False, agno_actual=2026) == "cnu_tabmor_cb2020h"
    assert _nombre("vigente", cnu.ROL_AFILIADO, True, agno_actual=2026) == "cnu_tabmor_rv2020m"
    assert _nombre("vigente", cnu.ROL_BENEFICIARIO, False, agno_actual=2026) == "cnu_tabmor_cb2020h"
    assert _nombre("vigente", cnu.ROL_BENEFICIARIO, True, agno_actual=2026) == "cnu_tabmor_b2020m"
    assert _nombre("vigente", cnu.ROL_INVALIDO, True, agno_actual=2026) == "cnu_tabmor_mi2020m"
    # Los calculos sin tabla usan las mismas.
    assert cnu.cnu_afiliado(65, rp=0.03, agno_actual=2026) == cnu.cnu_afiliado(65, tabla="cb2020", rp=0.03, agno_actual=2026)
    assert cnu.cnu_conyuge(65, 63, cony_mujer=True, rp=0.03, agno_actual=2026) == cnu.cnu_conyuge(
        65, 63, cony_mujer=True, tabla="cb2020", tabla_benef="b2020", rp=0.03, agno_actual=2026
    )
    assert cnu.cnu_sobrevivencia_conyuge(63, mujer=True, rp=0.03, agno_actual=2026) == cnu.cnu_sobrevivencia_conyuge(
        63, mujer=True, tabla_benef="b2020", rp=0.03, agno_actual=2026
    )


def test_vigente_sin_agno_actual_usa_el_agno_en_curso():
    esperado = cnu.cnu_afiliado(65, rp=0.03, agno_actual=cnu.core.agno_actual_por_defecto())
    assert cnu.cnu_afiliado(65, rp=0.03) == esperado


def test_convencion_fin_de_agno():
    assert tablas.fecha_fin_de_agno(2023) == 20231231
    # Sin fsiniestro: 31 de diciembre, por lo que 2023 y 2016 resuelven a la vigencia nueva.
    assert tablas.resolver_tabla("vigente", 0, "rv", "h", 2023) == ("cb", 2020)
    assert tablas.resolver_tabla("vigente", 0, "rv", "h", 2016) == ("cb", 2014)
    assert tablas.resolver_tabla("vigente", 0, "rv", "m", 2016) == ("rv", 2014)
    assert tablas.resolver_tabla("vigente", 0, "rv", "h", 2022) == ("cb", 2014)
    # Con fsiniestro manda la fecha del siniestro.
    assert tablas.resolver_tabla("vigente", 20230630, "rv", "h", 2023) == ("cb", 2014)
    assert _nombre("vigente", cnu.ROL_AFILIADO, False, agno_actual=2023) == "cnu_tabmor_cb2020h"
    assert _nombre("vigente", cnu.ROL_AFILIADO, False, fsiniestro=20230630, agno_actual=2023) == "cnu_tabmor_cb2014h"
    assert cnu.cnu_afiliado(65, rp=0.03, agno_actual=2023) == cnu.cnu_afiliado(65, tabla="cb2020", rp=0.03, agno_actual=2023)
    assert cnu.cnu_afiliado(65, fsiniestro=20230630, rp=0.03, agno_actual=2023) == cnu.cnu_afiliado(
        65, tabla="cb2014", rp=0.03, agno_actual=2023
    )


def test_vigente_requiere_rol_y_genero():
    with pytest.raises(ValueError, match="vigente"):
        tablas.resolver_tabla("vigente")


def test_vigente_2013_reproduce_valores_historicos():
    assert _nombre("vigente", cnu.ROL_AFILIADO, False, agno_actual=2013) == "cnu_tabmor_rv2009h"
    assert _nombre("vigente", cnu.ROL_BENEFICIARIO, True, agno_actual=2013) == "cnu_tabmor_b2006m"
    assert cnu.cnu_afiliado(65, agno_vector=2013, agno_actual=2013) == 13.016877
    assert cnu.cnu_conyuge(65, 63, agno_vector=2011, agno_actual=2011) == pytest.approx(2.231859, abs=1e-6)
    assert cnu.faj_afiliado(65, rp=0.03, agno_vector=2013, agno_actual=2014) == pytest.approx(0.066178, abs=1e-6)


def test_tabla_explicita_se_respeta():
    assert _nombre("rv2009", cnu.ROL_AFILIADO, False, agno_actual=2026) == "cnu_tabmor_rv2009h"
    assert cnu.cnu_afiliado(65, tabla="rv2009", rp=0.03, agno_actual=2026) == cnu.cnu_afiliado(
        65, tabla="rv2009", rp=0.03, agno_actual=2026, fsiniestro=0
    )
    assert cnu.cnu_afiliado(65, tabla="rv2009", rp=0.03, agno_actual=2026) != cnu.cnu_afiliado(65, rp=0.03, agno_actual=2026)


def test_faj_proyeccion_y_vectoriales_usan_la_misma_resolucion():
    kw = dict(rp=0.03, agno_actual=2026)
    exp = dict(tabla="cb2020", tabla_benef="b2020", rp=0.03, agno_actual=2026)
    assert cnu.faj_afiliado(65, 62, agno_vector=2013, **kw) == cnu.faj_afiliado(65, 62, agno_vector=2013, **exp)
    r = cnu.proyectar_pension(65, 62, saldo=1000.0, **kw)
    e = cnu.proyectar_pension(65, 62, saldo=1000.0, **exp)
    np.testing.assert_allclose(r.pension, e.pension)
    assert "cb2020 b2020" in r.descripcion
    np.testing.assert_allclose(cnu.proyectar_cnu(65, 62, **kw), cnu.proyectar_cnu(65, 62, **exp))
    # Vectoriales: cada fila resuelve con su propio agno y sexo.
    v = cnu.cnu_afiliado_vec([65, 65, 65], mujer=[False, True, False], rp=0.03, agno_actual=[2026, 2026, 2013])
    esperado = [
        cnu.cnu_afiliado(65, tabla="cb2020", rp=0.03, agno_actual=2026),
        cnu.cnu_afiliado(65, mujer=True, tabla="rv2020", rp=0.03, agno_actual=2026),
        cnu.cnu_afiliado(65, tabla="rv2009", rp=0.03, agno_actual=2013),
    ]
    np.testing.assert_allclose(v, esperado)
    v = cnu.cnu_conyuge_vec([65], [62], cony_mujer=True, **kw)
    assert v[0] == pytest.approx(cnu.cnu_conyuge(65, 62, cony_mujer=True, **exp))
    v = cnu.cnu_sobrevivencia_conyuge_vec([62], mujer=True, **kw)
    assert v[0] == pytest.approx(cnu.cnu_sobrevivencia_conyuge(62, mujer=True, tabla_benef="b2020", rp=0.03, agno_actual=2026))
    v = cnu.faj_afiliado_vec([65, 65], [62, 62], cony_mujer=True, rp=0.03, agno_actual=[2026, 2014])
    assert v[0] == pytest.approx(cnu.faj_afiliado_vec([65], [62], cony_mujer=True, **exp)[0])
    assert v[1] == pytest.approx(
        cnu.faj_afiliado_vec([65], [62], cony_mujer=True, rp=0.03, tabla="rv2009", tabla_benef="b2006", agno_actual=2014)[0]
    )


def test_combinacion_inexistente_da_error_claro():
    with pytest.raises(FileNotFoundError, match=r"cb2009h.*tablas_disponibles"):
        cnu.cnu_afiliado(65, tabla="cb2009", agno_actual=2026)
    with pytest.raises(FileNotFoundError, match=r"rv2020h.*tablas_disponibles"):
        cnu.cnu_afiliado(65, tabla="rv2020", agno_actual=2026)
    with pytest.raises(ValueError, match="solo existe para hombres"):
        cnu.cnu_afiliado(65, mujer=True, tabla="cb2020", agno_actual=2026)


def test_cli_default_vigente(capsys):
    for sub in ("afil", "conyuge", "sobrev", "faj", "proy"):
        with pytest.raises(SystemExit):
            construir_parser().parse_args([sub, "--help"])
        ayuda = " ".join(capsys.readouterr().out.split())  # argparse envuelve las lineas
        assert "por defecto: vigente" in ayuda
    assert main(["afil", "65", "--rp", "0.03", "--agno-actual", "2026"]) == 0
    out = capsys.readouterr().out
    assert "tabla cb2020h" in out
    assert float(out.strip().splitlines()[-1]) == cnu.cnu_afiliado(65, tabla="cb2020", rp=0.03, agno_actual=2026)
    main(["conyuge", "65", "63", "--rp", "0.03", "--agno-actual", "2026"])
    assert "tablas cb2020h b2020m" in capsys.readouterr().out
    main(["sobrev", "63", "--mujer", "--rp", "0.03", "--agno-actual", "2023"])
    assert "tabla b2020m" in capsys.readouterr().out
    main(["proy", "65", "62", "--rp", "0.03", "--agno-actual", "2026"])
    assert "cb2020 b2020" in capsys.readouterr().out
    main(["faj", "65", "--rp", "0.03", "--agno-vector", "2013", "--agno-actual", "2026"])
    assert float(capsys.readouterr().out.strip().splitlines()[-1]) == pytest.approx(
        cnu.faj_afiliado(65, tabla="cb2020", rp=0.03, agno_vector=2013, agno_actual=2026), abs=1e-6
    )

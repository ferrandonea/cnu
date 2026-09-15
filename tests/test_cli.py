import pytest

import cnu
from cnu.cli import CODIGO_ERROR_TASA, construir_parser, main


def test_afil(capsys):
    assert main(["afil", "65", "--agno-vector", "2013", "--agno-actual", "2013"]) == 0
    out = capsys.readouterr().out
    assert "13.016877" in out
    assert "vector 2013" in out


def test_afil_tabla_2020(capsys):
    assert main(["afil", "65", "--tabla", "cb2020", "--rp", "0.03", "--agno-actual", "2024"]) == 0
    out = capsys.readouterr().out
    assert "tabla cb2020" in out
    assert float(out.strip().splitlines()[-1]) > 0


def test_conyuge(capsys):
    main(["conyuge", "65", "63", "--agno-actual", "2011", "--agno-vector", "2011"])
    assert "2.231859" in capsys.readouterr().out


def test_faj(capsys):
    main(["faj", "65", "--rp", "0.03", "--agno-vector", "2013", "--agno-actual", "2014"])
    assert "0.066178" in capsys.readouterr().out


def test_proy_csv(capsys):
    main(["proy", "65", "--faj", "--csv", "--rp", "0.03", "--agno-actual", "2014"])
    lineas = capsys.readouterr().out.strip().splitlines()
    assert lineas[0] == "edad,saldo,faj,saldo_faj,pension"
    assert len(lineas) == 47


def test_proy_banda(capsys):
    assert main(["proy", "65", "--rp", "0.03", "--agno-actual", "2026"]) == 0
    lineas = capsys.readouterr().out.strip().splitlines()
    assert "con banda 10%" in lineas[0] and lineas[1].split() == ["edad", "saldo", "pension", "acotado"]
    assert lineas[2].split()[-1] == "0.000000" and any(l.split()[-1] == "1.000000" for l in lineas[2:])
    assert main(["proy", "65", "--sin-banda", "--rp", "0.03", "--agno-actual", "2026"]) == 0
    lineas = capsys.readouterr().out.strip().splitlines()
    assert "banda" not in lineas[0] and lineas[1].split() == ["edad", "saldo", "pension"]
    assert main(["proy", "65", "--banda", "--csv", "--rp", "0.03", "--agno-actual", "2014"]) == 0
    lineas = capsys.readouterr().out.strip().splitlines()
    assert lineas[0] == "edad,saldo,pension,acotado" and lineas[-1].endswith(",0") and any(l.endswith(",1") for l in lineas)
    assert main(["proy", "65", "--csv", "--rp", "0.03", "--agno-actual", "2014"]) == 0
    assert capsys.readouterr().out.splitlines()[0] == "edad,saldo,pension"
    # Con FAJ forzado se mantiene la advertencia de derogacion.
    assert main(["proy", "65", "--faj", "--banda", "--rp", "0.03", "--agno-actual", "2026"]) == 0
    out, err = capsys.readouterr()
    assert "con FAJ y banda 10%" in out.splitlines()[0] and "21.419" in err
    with pytest.raises(SystemExit):
        main(["proy", "65", "--banda", "--sin-banda", "--rp", "0.03"])


def test_tablas(capsys):
    main(["tablas"])
    out = capsys.readouterr().out
    assert "cnu_tabmor_rv2009h" in out
    lineas = {l.split()[0]: l for l in out.splitlines() if l.strip().startswith("cnu_tabmor_")}
    assert "factor historico" in lineas["cnu_tabmor_rv2009h"]
    assert "cnu_tabmor_cb2014h" in lineas and "factor historico" in lineas["cnu_tabmor_cb2014h"]
    assert "bidimensionales 2021-2036" in lineas["cnu_tabmor_cb2020h"]


def test_pasos(capsys):
    main(["afil", "65", "--pasos", "--agno-vector", "2013", "--agno-actual", "2013"])
    out = capsys.readouterr().out
    assert "t =   1:" in out
    assert "tabla rv2009h" in out


def test_fsiniestro_muestra_tabla_resuelta(capsys):
    assert main(["afil", "65", "--fsiniestro", "20240101", "--rp", "0.03", "--agno-actual", "2024"]) == 0
    out = capsys.readouterr().out
    assert "tabla cb2020h" in out
    main(["afil", "65", "--mujer", "--fsiniestro", "20240101", "--rp", "0.03", "--agno-actual", "2024"])
    assert "tabla rv2020m" in capsys.readouterr().out
    main(["conyuge", "65", "62", "--pasos", "--fsiniestro", "20240101", "--rp", "0.03", "--agno-actual", "2024"])
    out = capsys.readouterr().out
    assert "tablas cb2020h b2020m" in out
    assert out.count("tablas cb2020h b2020m") == 2  # pasos y descripcion


@pytest.mark.parametrize("argv", [
    ["afil", "65", "--agno-actual", "2026"],
    ["conyuge", "65", "63", "--agno-actual", "2026"],
    ["sobrev", "63", "--agno-actual", "2026"],
    ["faj", "65", "--agno-actual", "2014"],
    ["proy", "65", "--csv"],
])
def test_sin_tasa_falla_con_codigo_y_stderr(capsys, argv):
    assert main(argv) == CODIGO_ERROR_TASA != 0
    out, err = capsys.readouterr()
    assert out == ""
    assert "TITRP" in err and "--rp" in err
    assert "Traceback" not in err


def test_tasa_en_la_primera_linea(capsys):
    assert main(["afil", "65", "--rp", "0.0345", "--agno-actual", "2026"]) == 0
    lineas = capsys.readouterr().out.strip().splitlines()
    assert "tasa 3.45%" in lineas[0]
    assert lineas[-1].strip() == "14.755007"
    assert main(["afil", "65", "--fsiniestro", "20131231"]) == 0
    lineas = capsys.readouterr().out.strip().splitlines()
    assert "vector 2013" in lineas[0]
    assert float(lineas[-1]) > 0
    assert main(["afil", "65", "--pasos", "--rp", "0.03", "--agno-actual", "2026"]) == 0
    assert "tasa 3%" in capsys.readouterr().out.splitlines()[0]


def test_faj_y_proy_sin_default(capsys):
    assert main(["faj", "65", "--rp", "0.03", "--agno-vector", "2013", "--agno-actual", "2014"]) == 0
    lineas = capsys.readouterr().out.strip().splitlines()
    assert "tasa 3%" in lineas[0] and "0.066178" in lineas[-1]
    assert main(["faj", "65", "--fsiniestro", "20131231", "--agno-actual", "2013"]) == 0
    assert "vector 2013" in capsys.readouterr().out.splitlines()[0]
    assert main(["proy", "65", "--rp", "0.0345", "--agno-actual", "2026"]) == 0
    lineas = capsys.readouterr().out.strip().splitlines()
    assert "tasa 3.45%" in lineas[0] and len(lineas) == 48
    assert main(["proy", "65", "--csv", "--rp", "0.0345", "--agno-actual", "2026"]) == 0
    assert len(capsys.readouterr().out.strip().splitlines()) == 47


def test_vector_inexistente_falla_sin_traza(capsys):
    assert main(["afil", "65", "--agno-vector", "1999", "--agno-actual", "2013"]) == CODIGO_ERROR_TASA
    out, err = capsys.readouterr()
    assert out == "" and "1999" in err and "Traceback" not in err


def test_ayuda_sin_defaults_de_tasa():
    parser = construir_parser()
    ayudas = [parser.format_help()]
    for accion in parser._subparsers._group_actions[0].choices.values():
        ayudas.append(accion.format_help())
    for ayuda in ayudas:
        assert "2013" not in ayuda
        assert "0.03" not in ayuda


def test_hijo(capsys):
    assert main(["hijo", "65", "10", "--rp", "0.03", "--agno-actual", "2026"]) == 0
    lineas = capsys.readouterr().out.splitlines()
    assert lineas[0] == "CNU RP para hijo no inválido 15% (tablas cb2020h cb2020h), tasa 3% en el año 2026"
    assert lineas[-1].strip() == "0.135662"
    assert main(["hijo", "65", "21", "--hijo-mujer", "--pasos", "--rp", "0.03", "--agno-actual", "2026"]) == 0
    out = capsys.readouterr().out
    assert "hijo no inválido 15% (tablas cb2020h b2020m)" in out and "t =   1:" in out and "ajuste" in out
    assert out.strip().splitlines()[-1].strip() == "0.005165"
    assert main(["hijo", "65", "30", "--rp", "0.03", "--agno-actual", "2026"]) == 0
    assert capsys.readouterr().out.strip().splitlines()[-1].strip() == "0.000000"


def test_hijo_invalido(capsys):
    assert main(["hijo-inv", "65", "30", "--rp", "0.03", "--agno-actual", "2026"]) == 0
    lineas = capsys.readouterr().out.splitlines()
    assert lineas[0] == "CNU RP para hijo inválido total 15% (tablas cb2020h mi2020h), tasa 3% en el año 2026"
    assert lineas[-1].strip() == "1.257455"
    assert main(["hijo-inv", "65", "21", "--parcial", "--hijo-mujer", "--pasos", "--rp", "0.03",
                 "--agno-actual", "2026"]) == 0
    out = capsys.readouterr().out
    assert "hijo inválido parcial 15%/11% (tablas cb2020h mi2020m)" in out and "t =   1:" in out and "tramos" in out
    assert out.strip().splitlines()[-1].strip() == "1.259397"


def test_sobrev_hijo_invalido(capsys):
    assert main(["sobrev-hijo-inv", "21", "--mujer", "--rp", "0.03", "--agno-actual", "2026"]) == 0
    lineas = capsys.readouterr().out.splitlines()
    assert lineas[0] == "CNU RP para sobrevivencia de hijo inválido total 15% (tabla mi2020m), tasa 3% en el año 2026"
    assert lineas[-1].strip() == "3.939510"
    assert main(["sobrev-hijo-inv", "30.6", "--parcial", "--pasos", "--fsiniestro", "20131231"]) == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0].startswith("CNU RP para sobrevivencia de hijo inválido parcial 15%/11% (tabla mi2006h), vector 2013")
    assert "hijo 30.6 -> 31" in out.splitlines()[0] and "11% vitalicio desde los 24" in out
    for argv in (["hijo-inv", "65", "10", "--agno-actual", "2026"], ["sobrev-hijo-inv", "10", "--agno-actual", "2026"]):
        assert main(argv) == CODIGO_ERROR_TASA
        out, err = capsys.readouterr()
        assert out == "" and "TITRP" in err


def test_sobrev_hijo(capsys):
    assert main(["sobrev-hijo", "21", "--mujer", "--rp", "0.03", "--agno-actual", "2026"]) == 0
    lineas = capsys.readouterr().out.splitlines()
    assert lineas[0] == "CNU RP para sobrevivencia de hijo no inválido 15% (tabla b2020m), tasa 3% en el año 2026"
    assert lineas[-1].strip() == "0.431006"
    assert main(["sobrev-hijo", "10.6", "--pasos", "--fsiniestro", "20131231"]) == 0
    out = capsys.readouterr().out
    assert "vector 2013" in out.splitlines()[0] and "hijo 10.6 -> 11" in out.splitlines()[0]
    assert "tabla b2006h" in out and "ajuste" in out
    for argv in (["hijo", "65", "10", "--agno-actual", "2026"], ["sobrev-hijo", "10", "--agno-actual", "2026"]):
        assert main(argv) == CODIGO_ERROR_TASA
        out, err = capsys.readouterr()
        assert out == "" and "TITRP" in err


def test_conyuge_con_hijos(capsys):
    assert main(["conyuge-ch", "65", "63", "10", "--rp", "0.03", "--agno-actual", "2026"]) == 0
    lineas = capsys.readouterr().out.splitlines()
    assert lineas[0] == "CNU RP para cónyuge con hijos 50%/60% (tablas cb2020h b2020m), tasa 3% en el año 2026"
    assert lineas[-1].strip() == "2.409035"
    assert main(["conyuge-ch", "65", "63", "21.6", "--hijo-invalido", "--pasos", "--rp", "0.03", "--agno-actual", "2026"]) == 0
    out = capsys.readouterr().out
    assert "cónyuge con hijo inválido 50% (tablas cb2020h b2020m)" in out and "hijo 21.6 -> 22" in out
    assert "t =   1:" in out and "50% vitalicio" in out
    assert out.strip().splitlines()[-1].strip() == "2.077732"
    assert main(["conyuge-ch", "65", "63", "21", "--pasos", "--rp", "0.03", "--agno-actual", "2026"]) == 0
    out = capsys.readouterr().out
    assert "tramos: 50% *" in out and out.strip().splitlines()[-1].strip() == "2.489869"
    assert main(["conyuge-ch", "65", "63", "30", "--rp", "0.03", "--agno-actual", "2026"]) == 0
    assert capsys.readouterr().out.strip().splitlines()[-1].strip() == "2.493278"  # como sin hijos


def test_sobrev_conyuge_con_hijos(capsys):
    assert main(["sobrev-conyuge-ch", "63", "10", "--mujer", "--rp", "0.03", "--agno-actual", "2026"]) == 0
    lineas = capsys.readouterr().out.splitlines()
    assert lineas[0] == "CNU RP para sobrevivencia de cónyuge con hijos 50%/60% (tabla b2020m), tasa 3% en el año 2026"
    assert lineas[-1].strip() == "9.578224"
    assert main(["sobrev-conyuge-ch", "62.6", "10", "--hijo-invalido", "--fsiniestro", "20131231"]) == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0].startswith("CNU RP para sobrevivencia de cónyuge con hijo inválido 50% (tabla b2006h), vector 2013")
    assert "conyuge 62.6 -> 63" in out.splitlines()[0]
    for argv in (["conyuge-ch", "65", "63", "10", "--agno-actual", "2026"],
                 ["sobrev-conyuge-ch", "63", "10", "--agno-actual", "2026"]):
        assert main(argv) == CODIGO_ERROR_TASA
        out, err = capsys.readouterr()
        assert out == "" and "TITRP" in err


def test_conviviente_civil(capsys):
    assert main(["conyuge", "65", "63", "--conviviente", "--rp", "0.03", "--agno-actual", "2026"]) == 0
    lineas = capsys.readouterr().out.splitlines()
    assert lineas[0] == "CNU RP para conviviente civil sin hijos (tablas cb2020h b2020m), tasa 3% en el año 2026"
    assert lineas[-1].strip() == "2.493278"
    assert main(["conyuge", "65", "63", "--rp", "0.03", "--agno-actual", "2026"]) == 0
    assert capsys.readouterr().out.splitlines()[0].startswith("CNU RP para cónyuge sin hijos ")
    assert main(["sobrev", "63", "--mujer", "--conviviente", "--rp", "0.03", "--agno-actual", "2026"]) == 0
    lineas = capsys.readouterr().out.splitlines()
    assert lineas[0].startswith("CNU RP para sobrevivencia de conviviente civil sin hijos (tabla b2020m)")
    assert lineas[-1].strip() == "10.674379"
    assert main(["conyuge-ch", "65", "63", "10", "--conviviente", "--rp", "0.03", "--agno-actual", "2026"]) == 0
    lineas = capsys.readouterr().out.splitlines()
    assert lineas[0].startswith("CNU RP para conviviente civil con hijos 50%/60% ") and lineas[-1].strip() == "2.409035"
    assert main(["sobrev-conyuge-ch", "63", "10", "--mujer", "--conviviente", "--hijo-invalido", "--rp", "0.03",
                 "--agno-actual", "2026"]) == 0
    lineas = capsys.readouterr().out.splitlines()
    assert lineas[0].startswith("CNU RP para sobrevivencia de conviviente civil con hijo inválido 50% ")
    assert lineas[-1].strip() == "8.895316"


def test_madre_padre(capsys):
    assert main(["madre-padre", "50", "45", "21", "--rp", "0.03", "--agno-actual", "2026"]) == 0
    lineas = capsys.readouterr().out.splitlines()
    assert lineas[0] == "CNU RP para madre no matrimonial con hijos 30%/36% (tablas cb2020h b2020m), tasa 3% en el año 2026"
    assert lineas[-1].strip() == "1.370247"
    assert main(["madre-padre", "50", "45", "--rp", "0.03", "--agno-actual", "2026"]) == 0
    lineas = capsys.readouterr().out.splitlines()
    assert lineas[0].startswith("CNU RP para madre no matrimonial sin hijos 36% (tablas cb2020h b2020m)")
    assert lineas[-1].strip() == "1.370831"
    assert main(["madre-padre", "50", "45", "30", "--rp", "0.03", "--agno-actual", "2026"]) == 0
    lineas = capsys.readouterr().out.splitlines()
    assert lineas[0].startswith("CNU RP para madre no matrimonial sin hijos 36% ") and lineas[-1].strip() == "1.370831"
    assert main(["madre-padre", "50", "45", "21.6", "--hijo-invalido", "--pasos", "--rp", "0.03", "--agno-actual", "2026"]) == 0
    out = capsys.readouterr().out
    assert "madre no matrimonial con hijo inválido 30% (tablas cb2020h b2020m)" in out and "hijo 21.6 -> 22" in out
    assert "t =   1:" in out and "30% vitalicio" in out and out.strip().splitlines()[-1].strip() == "1.142359"
    assert main(["madre-padre", "50", "45", "21", "--pasos", "--rp", "0.03", "--agno-actual", "2026"]) == 0
    out = capsys.readouterr().out
    assert "tramos: 30% *" in out and out.strip().splitlines()[-1].strip() == "1.370247"
    assert main(["madre-padre", "48", "52.4", "10", "--padre", "--cot-mujer", "--rp", "0.03", "--agno-actual", "2026"]) == 0
    lineas = capsys.readouterr().out.splitlines()
    assert lineas[0].startswith("CNU RP para padre no matrimonial con hijos 30%/36% (tablas rv2020m cb2020h)")
    assert "madre o padre 52.4 -> 52" in lineas[0]
    assert lineas[-1].strip() == f"{cnu.cnu_madre_padre(48, 52, 10, cot_mujer=True, madre=False, rp=0.03, agno_actual=2026):9.6f}".strip()


def test_sobrev_madre_padre(capsys):
    assert main(["sobrev-madre-padre", "45", "21", "--rp", "0.03", "--agno-actual", "2026"]) == 0
    lineas = capsys.readouterr().out.splitlines()
    assert lineas[0] == "CNU RP para sobrevivencia de madre no matrimonial con hijos 30%/36% (tabla b2020m), tasa 3% en el año 2026"
    assert lineas[-1].strip() == "8.545539"
    assert main(["sobrev-madre-padre", "45", "--rp", "0.03", "--agno-actual", "2026"]) == 0
    lineas = capsys.readouterr().out.splitlines()
    assert lineas[0].startswith("CNU RP para sobrevivencia de madre no matrimonial sin hijos 36% ")
    assert lineas[-1].strip() == "8.717728"
    assert main(["sobrev-madre-padre", "44.6", "5", "--padre", "--hijo-invalido", "--fsiniestro", "20131231"]) == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0].startswith(
        "CNU RP para sobrevivencia de padre no matrimonial con hijo inválido 30% (tabla b2006h), vector 2013"
    )
    assert "madre o padre 44.6 -> 45" in out.splitlines()[0]
    for argv in (["madre-padre", "50", "45", "10", "--agno-actual", "2026"],
                 ["sobrev-madre-padre", "45", "--agno-actual", "2026"]):
        assert main(argv) == CODIGO_ERROR_TASA
        out, err = capsys.readouterr()
        assert out == "" and "TITRP" in err


def test_padres(capsys):
    assert main(["padres", "65", "88", "--rp", "0.03", "--agno-actual", "2026"]) == 0
    lineas = capsys.readouterr().out.splitlines()
    assert lineas[0] == "CNU RP para madre del afiliado 50% (tablas cb2020h b2020m), tasa 3% en el año 2026"
    assert lineas[-1].strip() == "0.161421"
    assert main(["padres", "65", "88.6", "--padre", "--pasos", "--rp", "0.03", "--agno-actual", "2026"]) == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0].startswith("CNU RP para padre del afiliado 50% (tablas cb2020h cb2020h)")
    assert "padre 88.6 -> 89" in out.splitlines()[0] and "t =   1:" in out
    assert out.strip().splitlines()[-1].strip() == f"{cnu.cnu_padres(65, 89, madre=False, rp=0.03, agno_actual=2026):9.6f}".strip()
    assert main(["sobrev-padres", "88", "--rp", "0.03", "--agno-actual", "2026"]) == 0
    lineas = capsys.readouterr().out.splitlines()
    assert lineas[0] == "CNU RP para sobrevivencia de madre del causante 50% (tabla b2020m), tasa 3% en el año 2026"
    assert lineas[-1].strip() == "3.089039"
    assert main(["sobrev-padres", "88", "--padre", "--fsiniestro", "20131231"]) == 0
    lineas = capsys.readouterr().out.splitlines()
    assert lineas[0].startswith("CNU RP para sobrevivencia de padre del causante 50% (tabla b2006h), vector 2013")
    for argv in (["padres", "65", "88", "--agno-actual", "2026"], ["sobrev-padres", "88", "--agno-actual", "2026"]):
        assert main(argv) == CODIGO_ERROR_TASA
        out, err = capsys.readouterr()
        assert out == "" and "TITRP" in err


def test_grupo(capsys):
    assert main(["grupo", "--afiliado", "65", "--hijo", "10", "--hijo", "14m", "--conyuge", "62m", "--hijo-inv", "20",
                 "total", "--rp", "0.03", "--agno-actual", "2026"]) == 0
    lineas = capsys.readouterr().out.splitlines()
    assert lineas[0] == ("CNU RP para grupo familiar: afiliado, cónyuge con hijo inválido 50%, hijo no inválido 15%, "
                         "hijo no inválido 15%, hijo inválido total 15% (tablas cb2020h b2020m mi2020h), tasa 3% en el año 2026")
    r = cnu.cnu_grupo_familiar(cnu.Afiliado(65), [cnu.Beneficiario("conyuge", 62), cnu.Beneficiario("hijo", 10),
                                                  cnu.Beneficiario("hijo", 14, True), cnu.Beneficiario("hijo_invalido", 20)],
                               rp=0.03, agno_actual=2026)
    assert len(lineas) == 7  # descripcion, cinco componentes y el total
    assert lineas[1].split()[0] == "afiliado" and lineas[1].split()[-1] == "15.456439"
    assert lineas[2].startswith("  cónyuge con hijo inválido 50%") and float(lineas[2].split()[-1]) == r.componentes[1].cnu
    assert lineas[-1].split() == ["total", f"{r.total:.6f}"]
    assert sum(float(l.split()[-1]) for l in lineas[1:-1]) == pytest.approx(r.total, abs=1e-6)
    # Ejemplo del README: afiliado con conyuge e hijo, y el mismo grupo en sobrevivencia con cuota mortuoria.
    assert main(["grupo", "--afiliado", "65", "--conyuge", "63", "--hijo", "10", "--rp", "0.03", "--agno-actual", "2026"]) == 0
    lineas = capsys.readouterr().out.splitlines()
    assert lineas[0] == ("CNU RP para grupo familiar: afiliado, cónyuge con hijos 50%/60%, hijo no inválido 15% "
                         "(tablas cb2020h b2020m), tasa 3% en el año 2026")
    assert lineas[-1].split() == ["total", "18.001136"]
    assert main(["grupo", "--conyuge", "63m", "--hijo", "10m", "--uf", "1", "--rp", "0.03", "--agno-actual", "2026"]) == 0
    lineas = capsys.readouterr().out.splitlines()
    assert lineas[0].startswith("CNU RP para sobrevivencia de grupo familiar: cónyuge con hijos 50%/60%, hijo no inválido 15%,"
                                " cuota mortuoria 15 UF (tabla b2020m)")
    assert lineas[3].split() == ["cuota", "mortuoria", "15", "UF", "15.000000"]
    assert lineas[-1].split() == ["total", "26.298419"]


def test_grupo_edad_actuarial_pasos_y_sexos(capsys):
    assert main(["grupo", "--afiliado", "65.6", "--conyuge", "62.5m", "--hijo", "10", "--pasos", "--rp", "0.03",
                 "--agno-actual", "2026"]) == 0
    out = capsys.readouterr().out
    assert "[edad actuarial: afiliado 65.6 -> 66, conyuge 1 62.5 -> 63]" in out.splitlines()[0]
    assert "--- afiliado ---" in out and "t =   1:" in out and out.count("--- ") == 3
    assert out.strip().splitlines()[-1].split()[-1] == f"{cnu.cnu_grupo_familiar(66, [('conyuge', 63), ('hijo', 10)], rp=0.03, agno_actual=2026).total:.6f}"
    assert main(["grupo", "--afiliado", "60m", "--conviviente", "65h", "--madre-padre", "48h", "--hijo-inv", "21m", "parcial",
                 "--rp", "0.03", "--agno-actual", "2026"]) == 0
    lineas = capsys.readouterr().out.splitlines()
    assert lineas[0].startswith("CNU RP para grupo familiar: afiliado, conviviente civil con hijo inválido 50%, "
                                "padre no matrimonial con hijo inválido 30%, hijo inválido parcial 15%/11% "
                                "(tablas rv2020m cb2020h mi2020m)")
    assert main(["grupo", "--afiliado", "65", "--padres", "88", "--padres", "90h", "--rp", "0.03", "--agno-actual", "2026"]) == 0
    lineas = capsys.readouterr().out.splitlines()
    assert "madre del afiliado 50%, padre del afiliado 50%" in lineas[0]
    assert lineas[-1].split()[-1] == "15.704435"


def test_grupo_errores(capsys):
    from cnu.cli import CODIGO_ERROR_GRUPO

    assert main(["grupo", "--afiliado", "65", "--padres", "88", "--conyuge", "62m", "--rp", "0.03", "--agno-actual", "2026"]) == CODIGO_ERROR_GRUPO
    out, err = capsys.readouterr()
    assert out == "" and "articulo 58" in err and "Traceback" not in err and "--rp" not in err
    assert main(["grupo", "--afiliado", "65", "--hijo", "10", "--rp", "0.03", "--agno-actual", "2026"]) == CODIGO_ERROR_GRUPO
    out, err = capsys.readouterr()
    assert out == "" and "0,5/n" in err
    assert main(["grupo", "--afiliado", "65", "--conyuge", "63", "--hijo-inv", "20", "total", "parcial", "--rp", "0.03",
                 "--agno-actual", "2026"]) == CODIGO_ERROR_GRUPO
    out, err = capsys.readouterr()
    assert out == "" and "--hijo-inv" in err
    assert main(["grupo", "--afiliado", "65", "--conyuge", "63", "--agno-actual", "2026"]) == CODIGO_ERROR_TASA
    out, err = capsys.readouterr()
    assert out == "" and "TITRP" in err and "--rp" in err
    with pytest.raises(SystemExit) as e:
        main(["grupo", "--afiliado", "65", "--hijo", "10x", "--rp", "0.03"])
    assert e.value.code == 2 and "62m" in capsys.readouterr().err

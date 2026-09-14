import pytest

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

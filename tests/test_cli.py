import pytest

from cnu.cli import main


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
    main(["proy", "65", "--faj", "--csv", "--agno-actual", "2014"])
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

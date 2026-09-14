import pytest

from cnu.cli import main


def test_afil(capsys):
    assert main(["afil", "65", "--agno-actual", "2013"]) == 0
    out = capsys.readouterr().out
    assert "13.016877" in out
    assert "vector 2013" in out


def test_conyuge(capsys):
    main(["conyuge", "65", "63", "--agno-actual", "2011", "--agno-vector", "2011"])
    assert "2.231859" in capsys.readouterr().out


def test_faj(capsys):
    main(["faj", "65", "--rp", "0.03", "--agno-actual", "2014"])
    assert "0.066178" in capsys.readouterr().out


def test_proy_csv(capsys):
    main(["proy", "65", "--faj", "--csv", "--agno-actual", "2014"])
    lineas = capsys.readouterr().out.strip().splitlines()
    assert lineas[0] == "edad,saldo,faj,saldo_faj,pension"
    assert len(lineas) == 47


def test_tablas(capsys):
    main(["tablas"])
    assert "cnu_tabmor_rv2009h" in capsys.readouterr().out


def test_pasos(capsys):
    main(["afil", "65", "--pasos", "--agno-actual", "2013"])
    assert "t =   1:" in capsys.readouterr().out

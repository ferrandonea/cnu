"""Interfaz de linea de comandos: ``cnu <subcomando> ...``."""

from __future__ import annotations

import argparse
import csv
import sys

from . import __version__, core, faj as _faj, proyeccion, tablas


def _opciones_comunes(p: argparse.ArgumentParser, benef: bool, afil: bool = True) -> None:
    if afil:
        p.add_argument("--tabla", default=core.TABLA_AFILIADO,
                       help="tabla del afiliado (p.ej. rv2009, cb2020; por defecto: %(default)s)")
    if benef:
        p.add_argument("--tabla-benef", default=core.TABLA_BENEFICIARIO,
                       help="tabla del beneficiario (p.ej. b2006, b2020; por defecto: %(default)s)")
    p.add_argument("--agno-vector", type=int, default=core.AGNO_VECTOR, help="año del vector de tasas")
    p.add_argument("--agno-actual", type=int, default=None,
                   help="año de cálculo (por defecto, el actual); la tabla vigente es la del 31 de diciembre")
    p.add_argument("--fsiniestro", type=int, default=0, help="fecha del siniestro YYYYMMDD (asigna la tabla)")
    p.add_argument("--dir-tablas", default=None, help="directorio con tablas de mortalidad propias")
    p.add_argument("--dir-vectores", default=None, help="directorio con vectores de tasas propios")


def _opciones_tasa(p: argparse.ArgumentParser) -> None:
    g = p.add_mutually_exclusive_group()
    g.add_argument("--rv", type=float, default=None, help="tasa de renta vitalicia")
    g.add_argument("--rp", type=float, default=None, help="tasa única de retiro programado")
    p.add_argument("--pasos", action="store_true", help="imprime el cálculo periodo a periodo")


def _opciones_faj(p: argparse.ArgumentParser) -> None:
    p.add_argument("--edad-maxima", type=int, default=_faj.EDAD_MAXIMA_FAJ, help="edad hasta la que cubre el FAJ")
    p.add_argument("--saldo", type=float, default=1.0, help="saldo al momento del retiro")
    p.add_argument("--pcent", type=float, default=_faj.PCENT, help="porcentaje de la primera pensión a cubrir")
    p.add_argument("--rp0", type=float, default=None, help="pensión de referencia")
    p.add_argument("--criter", type=float, default=_faj.CRITERIO, help="precisión de la búsqueda")
    p.add_argument("--maxiter", type=int, default=_faj.MAXITER, help="máximo de iteraciones")


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cnu",
        description="Calculador del Capital Necesario Unitario (CNU) del sistema de pensiones chileno.",
    )
    parser.add_argument("--version", action="version", version=f"cnu {__version__}")
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("afil", help="CNU para afiliado (cnu_afili)")
    p.add_argument("x", type=int, help="edad del afiliado")
    p.add_argument("--mujer", action="store_true", help="el afiliado es mujer")
    _opciones_comunes(p, benef=False)
    _opciones_tasa(p)

    p = sub.add_parser("conyuge", help="CNU para cónyuge sin hijos (cnu_cnyg_s_hi)")
    p.add_argument("x", type=int, help="edad del afiliado")
    p.add_argument("y", type=int, help="edad del cónyuge")
    p.add_argument("--cot-mujer", action="store_true", help="el afiliado es mujer")
    p.add_argument("--cony-hombre", action="store_true", help="el cónyuge es hombre (por defecto, mujer)")
    _opciones_comunes(p, benef=True)
    _opciones_tasa(p)

    p = sub.add_parser("sobrev", help="CNU de sobrevivencia para cónyuge sin hijos (cnu_sobr_cnyg_s_hi)")
    p.add_argument("y", type=int, help="edad del cónyuge")
    p.add_argument("--mujer", action="store_true", help="el cónyuge es mujer")
    _opciones_comunes(p, benef=True, afil=False)
    _opciones_tasa(p)

    p = sub.add_parser("faj", help="Factor de Ajuste (cnu_faji)")
    p.add_argument("x", type=int, help="edad del afiliado")
    p.add_argument("y", type=int, nargs="?", default=None, help="edad del cónyuge (opcional)")
    p.add_argument("--cot-mujer", action="store_true", help="el afiliado es mujer")
    p.add_argument("--cony-hombre", action="store_true", help="el cónyuge es hombre (por defecto, mujer)")
    p.add_argument("--rp", type=float, default=0.03, help="tasa de retiro programado (nan = usar vector)")
    _opciones_comunes(p, benef=True)
    _opciones_faj(p)

    p = sub.add_parser("proy", help="Proyección de pensión en retiro programado (cnu_proy_pensi)")
    p.add_argument("x", type=int, help="edad del afiliado")
    p.add_argument("y", type=int, nargs="?", default=None, help="edad del cónyuge (opcional)")
    p.add_argument("--cot-mujer", action="store_true", help="el afiliado es mujer")
    p.add_argument("--cony-hombre", action="store_true", help="el cónyuge es hombre (por defecto, mujer)")
    p.add_argument("--rp", type=float, default=0.03, help="tasa de retiro programado (nan = usar vector)")
    p.add_argument("--faj", action="store_true", help="incluye Factor de Ajuste")
    p.add_argument("--csv", action="store_true", help="imprime el resultado como CSV")
    _opciones_comunes(p, benef=True)
    _opciones_faj(p)

    p = sub.add_parser("tablas", help="lista las tablas y vectores incluidos")
    return parser


def _nan_a_none(v):
    return None if v is None or v != v else v


def main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)
    c = args.comando
    if c == "tablas":
        print("Tablas de mortalidad:")
        for t in tablas.tablas_disponibles():
            print(f"  {t:24s} {tablas.describir_tabla(t)}")
        print("Vectores de tasas:")
        for v in tablas.vectores_disponibles():
            print(f"  cnu_vec{v}")
        return 0

    comunes = dict(agno_vector=args.agno_vector, agno_actual=args.agno_actual, fsiniestro=args.fsiniestro,
                   dir_tablas=args.dir_tablas, dir_vectores=args.dir_vectores)

    if c == "afil":
        v = core.cnu_afiliado(args.x, args.mujer, args.tabla, rv=args.rv, rp=args.rp, pasos=args.pasos, **comunes)
        print(core.describir("soltero sin hijos", args.tabla, None, args.agno_vector, args.agno_actual,
                             args.rv, args.rp, args.fsiniestro, mujer=args.mujer, dir_tablas=args.dir_tablas))
        print(f"{v:9.6f}")
    elif c == "conyuge":
        v = core.cnu_conyuge(args.x, args.y, args.cot_mujer, not args.cony_hombre, args.tabla, args.tabla_benef,
                             rv=args.rv, rp=args.rp, pasos=args.pasos, **comunes)
        print(core.describir("conyuge sin hijos", args.tabla, args.tabla_benef, args.agno_vector,
                             args.agno_actual, args.rv, args.rp, args.fsiniestro,
                             mujer=args.cot_mujer, benef_mujer=not args.cony_hombre, dir_tablas=args.dir_tablas))
        print(f"{v:9.6f}")
    elif c == "sobrev":
        v = core.cnu_sobrevivencia_conyuge(args.y, args.mujer, args.tabla_benef, rv=args.rv, rp=args.rp,
                                           pasos=args.pasos, **comunes)
        print(core.describir("sobrevivencia de conyuge sin hijos", None, args.tabla_benef, args.agno_vector,
                             args.agno_actual, args.rv, args.rp, args.fsiniestro,
                             benef_mujer=args.mujer, dir_tablas=args.dir_tablas))
        print(f"{v:9.6f}")
    elif c == "faj":
        v = _faj.faj_afiliado(
            args.x, args.y, args.cot_mujer, not args.cony_hombre, args.tabla, args.tabla_benef,
            rp=_nan_a_none(args.rp), edad_maxima=args.edad_maxima, saldo=args.saldo, pcent=args.pcent,
            rp0=args.rp0, criter=args.criter, maxiter=args.maxiter, **comunes,
        )
        quien = "afiliado soltero" if args.y is None else "afiliado con conyuge"
        print(f"FAJ para {quien}")
        print(f"{v:9.6f}")
    elif c == "proy":
        r = proyeccion.proyectar_pension(
            args.x, args.y, args.saldo, args.cot_mujer, not args.cony_hombre, args.tabla, args.tabla_benef,
            rp=_nan_a_none(args.rp), faj=args.faj, edad_maxima=args.edad_maxima, pcent=args.pcent,
            rp0=args.rp0, criter=args.criter, maxiter=args.maxiter, **comunes,
        )
        cols = r.columnas()
        if args.csv:
            w = csv.writer(sys.stdout)
            w.writerow(cols)
            w.writerows(zip(*cols.values()))
        else:
            print(r.descripcion)
            print("".join(f"{k:>12}" for k in cols))
            for fila in zip(*cols.values()):
                print("".join(f"{v:12.6f}" for v in fila))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

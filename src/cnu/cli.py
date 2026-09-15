"""Interfaz de linea de comandos: ``cnu <subcomando> ...``."""

from __future__ import annotations

import argparse
import csv
import re
import sys
import warnings

from . import __version__, core, faj as _faj, grupo as _grupo, proyeccion, tablas
from .grupo import etiqueta_conyuge, etiqueta_hijo_invalido, etiqueta_madre_padre, etiqueta_padres  # noqa: F401


def _opciones_comunes(p: argparse.ArgumentParser, benef: bool, afil: bool = True) -> None:
    if afil:
        p.add_argument("--tabla", default=core.TABLA_AFILIADO,
                       help="tabla del afiliado (p.ej. rv2009, cb2020; por defecto: %(default)s)")
    if benef:
        p.add_argument("--tabla-benef", default=core.TABLA_BENEFICIARIO,
                       help="tabla del beneficiario (p.ej. b2006, b2020; por defecto: %(default)s)")
    p.add_argument("--agno-vector", type=int, default=core.AGNO_VECTOR,
                   help="año del vector de tasas de retiro programado (sin tasa por defecto: ver --rp)")
    p.add_argument("--agno-actual", type=int, default=None,
                   help="año de cálculo (por defecto, el actual); la tabla vigente es la del 31 de diciembre")
    p.add_argument("--fsiniestro", type=int, default=0,
                   help="fecha del siniestro YYYYMMDD (asigna la tabla; anterior a 2014, el vector de tasas de su año)")
    p.add_argument("--dir-tablas", default=None, help="directorio con tablas de mortalidad propias")
    p.add_argument("--dir-vectores", default=None, help="directorio con vectores de tasas propios")


def _opciones_tasa(p: argparse.ArgumentParser) -> None:
    g = p.add_mutually_exclusive_group()
    g.add_argument("--rv", type=float, default=None, help="tasa de renta vitalicia")
    g.add_argument("--rp", type=float, default=None, help="tasa única de retiro programado (TITRP)")
    p.add_argument("--pasos", action="store_true", help="imprime el cálculo periodo a periodo")


def _opcion_conviviente(p: argparse.ArgumentParser) -> None:
    p.add_argument("--conviviente", action="store_true",
                   help="el beneficiario es conviviente civil (misma fórmula y valor que el cónyuge)")


def _opcion_hijo_invalido(p: argparse.ArgumentParser) -> None:
    p.add_argument("--hijo-invalido", action="store_true",
                   help="algún hijo con derecho a pensión es inválido: 50%% vitalicio (la edad h no interviene)")


def _opcion_padre(p: argparse.ArgumentParser, quien: str) -> None:
    p.add_argument("--padre", action="store_true", help=f"el beneficiario es el padre {quien} (por defecto, la madre)")


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
    p.add_argument("x", type=float, help="edad del afiliado (admite decimales; se redondea a edad actuarial)")
    p.add_argument("--mujer", action="store_true", help="el afiliado es mujer")
    _opciones_comunes(p, benef=False)
    _opciones_tasa(p)

    p = sub.add_parser("conyuge", help="CNU para cónyuge o conviviente civil sin hijos, 60%% (cnu_cnyg_s_hi)")
    p.add_argument("x", type=float, help="edad del afiliado (admite decimales; se redondea a edad actuarial)")
    p.add_argument("y", type=float, help="edad del cónyuge (admite decimales; se redondea a edad actuarial)")
    p.add_argument("--cot-mujer", action="store_true", help="el afiliado es mujer")
    p.add_argument("--cony-hombre", action="store_true", help="el cónyuge es hombre (por defecto, mujer)")
    _opcion_conviviente(p)
    _opciones_comunes(p, benef=True)
    _opciones_tasa(p)

    p = sub.add_parser("sobrev", help="CNU de sobrevivencia para cónyuge o conviviente civil sin hijos, 60%%"
                                      " (cnu_sobr_cnyg_s_hi)")
    p.add_argument("y", type=float, help="edad del cónyuge (admite decimales; se redondea a edad actuarial)")
    p.add_argument("--mujer", action="store_true", help="el cónyuge es mujer")
    _opcion_conviviente(p)
    _opciones_comunes(p, benef=True, afil=False)
    _opciones_tasa(p)

    p = sub.add_parser("conyuge-ch", help="CNU para cónyuge o conviviente civil con hijos con derecho a pensión,"
                                          " 50%% hasta los 24 años del hijo menor y 60%% después")
    p.add_argument("x", type=float, help="edad del afiliado (admite decimales; se redondea a edad actuarial)")
    p.add_argument("y", type=float, help="edad del cónyuge (admite decimales; se redondea a edad actuarial)")
    p.add_argument("h", type=float, help="edad del hijo menor con derecho a pensión, desde 0 (se redondea a edad actuarial)")
    p.add_argument("--cot-mujer", action="store_true", help="el afiliado es mujer")
    p.add_argument("--cony-hombre", action="store_true", help="el cónyuge es hombre (por defecto, mujer)")
    _opcion_hijo_invalido(p)
    _opcion_conviviente(p)
    _opciones_comunes(p, benef=True)
    _opciones_tasa(p)

    p = sub.add_parser("sobrev-conyuge-ch", help="CNU de sobrevivencia para cónyuge o conviviente civil con hijos"
                                                 " con derecho a pensión, 50%%/60%%")
    p.add_argument("y", type=float, help="edad del cónyuge (admite decimales; se redondea a edad actuarial)")
    p.add_argument("h", type=float, help="edad del hijo menor con derecho a pensión, desde 0 (se redondea a edad actuarial)")
    p.add_argument("--mujer", action="store_true", help="el cónyuge es mujer")
    _opcion_hijo_invalido(p)
    _opcion_conviviente(p)
    _opciones_comunes(p, benef=True, afil=False)
    _opciones_tasa(p)

    p = sub.add_parser("hijo", help="CNU para hijo no inválido, 15%% (pensión de vejez o invalidez)")
    p.add_argument("x", type=float, help="edad del afiliado (admite decimales; se redondea a edad actuarial)")
    p.add_argument("h", type=float, help="edad del hijo, desde 0 (admite decimales; se redondea a edad actuarial)")
    p.add_argument("--cot-mujer", action="store_true", help="el afiliado es mujer")
    p.add_argument("--hijo-mujer", action="store_true", help="el hijo es mujer (por defecto, hombre)")
    _opciones_comunes(p, benef=True)
    _opciones_tasa(p)

    p = sub.add_parser("sobrev-hijo", help="CNU de sobrevivencia para hijo no inválido, 15%%")
    p.add_argument("h", type=float, help="edad del hijo, desde 0 (admite decimales; se redondea a edad actuarial)")
    p.add_argument("--mujer", action="store_true", help="el hijo es mujer (por defecto, hombre)")
    _opciones_comunes(p, benef=True, afil=False)
    _opciones_tasa(p)

    p = sub.add_parser("hijo-inv", help="CNU para hijo inválido, total 15%% o parcial 15%%/11%% (pensión de vejez o invalidez)")
    p.add_argument("x", type=float, help="edad del afiliado (admite decimales; se redondea a edad actuarial)")
    p.add_argument("h", type=float, help="edad del hijo inválido, desde 0 y sin edad límite (se redondea a edad actuarial)")
    p.add_argument("--cot-mujer", action="store_true", help="el afiliado es mujer")
    p.add_argument("--hijo-mujer", action="store_true", help="el hijo es mujer (por defecto, hombre)")
    p.add_argument("--parcial", action="store_true",
                   help="invalidez parcial: 15%% hasta los 24 años y 11%% después (por defecto, total: 15%% vitalicio)")
    _opciones_comunes(p, benef=True)
    _opciones_tasa(p)

    p = sub.add_parser("sobrev-hijo-inv", help="CNU de sobrevivencia para hijo inválido, total 15%% o parcial 15%%/11%%")
    p.add_argument("h", type=float, help="edad del hijo inválido, desde 0 y sin edad límite (se redondea a edad actuarial)")
    p.add_argument("--mujer", action="store_true", help="el hijo es mujer (por defecto, hombre)")
    p.add_argument("--parcial", action="store_true",
                   help="invalidez parcial: 15%% hasta los 24 años y 11%% después (por defecto, total: 15%% vitalicio)")
    _opciones_comunes(p, benef=True, afil=False)
    _opciones_tasa(p)

    p = sub.add_parser("madre-padre", help="CNU para madre o padre de hijos de filiación no matrimonial, 36%% sin"
                                           " hijos con derecho a pensión y 30%% mientras los haya")
    p.add_argument("x", type=float, help="edad del afiliado (admite decimales; se redondea a edad actuarial)")
    p.add_argument("u", type=float, help="edad de la madre o el padre (admite decimales; se redondea a edad actuarial)")
    p.add_argument("h", type=float, nargs="?", default=None,
                   help="edad del hijo menor con derecho a pensión, desde 0; sin ella, sin hijos con derecho (36%%)")
    p.add_argument("--cot-mujer", action="store_true", help="el afiliado es mujer")
    _opcion_padre(p, "de los hijos")
    p.add_argument("--hijo-invalido", action="store_true",
                   help="algún hijo con derecho a pensión es inválido: 30%% vitalicio (la edad h no interviene)")
    _opciones_comunes(p, benef=True)
    _opciones_tasa(p)

    p = sub.add_parser("sobrev-madre-padre", help="CNU de sobrevivencia para madre o padre de hijos de filiación"
                                                  " no matrimonial, 36%% sin hijos con derecho y 30%% mientras los haya")
    p.add_argument("u", type=float, help="edad de la madre o el padre (admite decimales; se redondea a edad actuarial)")
    p.add_argument("h", type=float, nargs="?", default=None,
                   help="edad del hijo menor con derecho a pensión, desde 0; sin ella, sin hijos con derecho (36%%)")
    _opcion_padre(p, "de los hijos")
    p.add_argument("--hijo-invalido", action="store_true",
                   help="algún hijo con derecho a pensión es inválido: 30%% vitalicio (la edad h no interviene)")
    _opciones_comunes(p, benef=True, afil=False)
    _opciones_tasa(p)

    p = sub.add_parser("padres", help="CNU para la madre o el padre del afiliado, 50%% cada uno (uno por llamada)")
    p.add_argument("x", type=float, help="edad del afiliado (admite decimales; se redondea a edad actuarial)")
    p.add_argument("m", type=float, help="edad de la madre o el padre del afiliado (se redondea a edad actuarial)")
    p.add_argument("--cot-mujer", action="store_true", help="el afiliado es mujer")
    _opcion_padre(p, "del afiliado")
    _opciones_comunes(p, benef=True)
    _opciones_tasa(p)

    p = sub.add_parser("sobrev-padres", help="CNU de sobrevivencia para la madre o el padre del causante, 50%% cada uno")
    p.add_argument("m", type=float, help="edad de la madre o el padre del causante (se redondea a edad actuarial)")
    _opcion_padre(p, "del causante")
    _opciones_comunes(p, benef=True, afil=False)
    _opciones_tasa(p)

    p = sub.add_parser("grupo", help="CNU total de un grupo familiar con el aporte de cada beneficiario (Anexo N° 7);"
                                     " sin --afiliado, pensión de sobrevivencia")
    p.add_argument("--afiliado", type=_persona, default=None, metavar="EDAD[h|m]",
                   help="edad y sexo del afiliado (p.ej. 65 o 60m; por defecto hombre); sin él, sobrevivencia")
    p.add_argument("--conyuge", type=_persona, action="append", default=[], metavar="EDAD[h|m]",
                   help="cónyuge (por defecto mujer; 62m, 65h)")
    p.add_argument("--conviviente", type=_persona, action="append", default=[], metavar="EDAD[h|m]",
                   help="conviviente civil (misma fórmula que el cónyuge; por defecto mujer)")
    p.add_argument("--hijo", type=_persona, action="append", default=[], metavar="EDAD[h|m]",
                   help="hijo no inválido, repetible (por defecto hombre; 10, 14m)")
    p.add_argument("--hijo-inv", type=_persona, action="append", default=[], nargs="+", metavar="EDAD[h|m] [total|parcial]",
                   help="hijo inválido, repetible: edad y sexo más el grado (por defecto total; 20 total, 21m parcial)")
    p.add_argument("--madre-padre", type=_persona, action="append", default=[], metavar="EDAD[h|m]",
                   help="madre (m, por defecto) o padre (h) de hijos de filiación no matrimonial, repetible")
    p.add_argument("--padres", type=_persona, action="append", default=[], metavar="EDAD[h|m]",
                   help="madre (m, por defecto) o padre (h) del afiliado, repetible (a lo más uno de cada uno)")
    p.add_argument("--uf", type=float, default=None, metavar="VALOR_UF",
                   help="valor de la UF en las unidades del saldo: agrega la cuota mortuoria (15 UF) como componente")
    _opciones_comunes(p, benef=True)
    _opciones_tasa(p)

    p = sub.add_parser("faj", help="Factor de Ajuste (cnu_faji); derogado desde el 1-2-2022 (Ley 21.419)")
    p.add_argument("x", type=float, help="edad del afiliado (admite decimales; se redondea a edad actuarial)")
    p.add_argument("y", type=float, nargs="?", default=None,
                   help="edad del cónyuge, opcional (admite decimales; se redondea a edad actuarial)")
    p.add_argument("--cot-mujer", action="store_true", help="el afiliado es mujer")
    p.add_argument("--cony-hombre", action="store_true", help="el cónyuge es hombre (por defecto, mujer)")
    p.add_argument("--rp", type=float, default=None, help="tasa única de retiro programado (TITRP)")
    _opciones_comunes(p, benef=True)
    _opciones_faj(p)

    p = sub.add_parser("proy", help="Proyección de pensión en retiro programado (cnu_proy_pensi)")
    p.add_argument("x", type=float, help="edad del afiliado (admite decimales; se redondea a edad actuarial)")
    p.add_argument("y", type=float, nargs="?", default=None,
                   help="edad del cónyuge, opcional (admite decimales; se redondea a edad actuarial)")
    p.add_argument("--cot-mujer", action="store_true", help="el afiliado es mujer")
    p.add_argument("--cony-hombre", action="store_true", help="el cónyuge es hombre (por defecto, mujer)")
    p.add_argument("--rp", type=float, default=None, help="tasa única de retiro programado (TITRP)")
    p.add_argument("--faj", action="store_true",
                   help="incluye Factor de Ajuste (derogado desde el 1-2-2022, Ley 21.419)")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--banda", dest="banda", action="store_true", default=None,
                   help="fuerza la banda de variación máxima del 10%% (Ley 21.735; por defecto rige "
                        "con fecha de cálculo desde el 1-9-2025)")
    g.add_argument("--sin-banda", dest="banda", action="store_false", help="desactiva la banda del 10%%")
    p.add_argument("--csv", action="store_true", help="imprime el resultado como CSV")
    _opciones_comunes(p, benef=True)
    _opciones_faj(p)

    p = sub.add_parser("tablas", help="lista las tablas y vectores incluidos")
    return parser


_PERSONA = re.compile(r"^(\d+(?:\.\d+)?)([hm])?$", re.IGNORECASE)


def _persona(texto: str):
    """``EDAD[h|m]`` -> ``(edad, mujer)``; ``mujer`` es ``None`` sin sufijo (sexo por defecto del tipo).

    Los tokens ``total`` y ``parcial`` (grado del hijo inválido) se devuelven tal cual."""
    if texto.lower() in ("total", "parcial"):
        return texto.lower()
    m = _PERSONA.match(texto.strip())
    if not m:
        raise argparse.ArgumentTypeError(f"se esperaba una edad con sufijo opcional h o m (p.ej. 62m), no {texto!r}")
    sexo = m.group(2)
    return float(m.group(1)), None if sexo is None else sexo.lower() == "m"


def _beneficiarios_cli(args) -> list:
    """Lista de :class:`cnu.Beneficiario` a partir de las opciones repetibles de ``cnu grupo``."""
    benef = []
    for tipo, personas in ((_grupo.TIPO_CONYUGE, args.conyuge), (_grupo.TIPO_CONVIVIENTE, args.conviviente),
                           (_grupo.TIPO_HIJO, args.hijo), (_grupo.TIPO_MADRE_PADRE, args.madre_padre),
                           (_grupo.TIPO_PADRES, args.padres)):
        benef.extend(_grupo.Beneficiario(tipo, edad, mujer) for edad, mujer in personas)
    for tokens in args.hijo_inv:
        edades = [t for t in tokens if isinstance(t, tuple)]
        grados = [t for t in tokens if isinstance(t, str)]
        if len(edades) != 1 or len(grados) > 1:
            raise _grupo.ErrorGrupoFamiliar(
                "--hijo-inv recibe una edad con sufijo opcional h o m y, opcionalmente, el grado total o parcial "
                "(p.ej. --hijo-inv 20 total)"
            )
        (edad, mujer), = edades
        benef.append(_grupo.Beneficiario(_grupo.TIPO_HIJO_INVALIDO, edad, mujer, parcial=grados == ["parcial"]))
    return benef


def _nan_a_none(v):
    return None if v is None or v != v else v


def _etiqueta_tasa(rv, rp, agno_vector, fsiniestro) -> str:
    """Tasa efectiva para la primera linea de salida (``tasa 3.45%`` o ``vector 2013``)."""
    if rv is not None:
        return f"tasa {rv * 100:g}%"
    if rp is not None:
        return f"tasa {rp * 100:g}%"
    return f"vector {core.agno_vector_efectivo(agno_vector, fsiniestro)}"


def _nota_edades(**edades) -> str:
    """Sufijo para la primera linea con las edades actuariales usadas, si difieren de las entregadas."""
    notas = [f"{nombre} {valor:g} -> {core.edad_entera(valor)}"
             for nombre, valor in edades.items()
             if valor is not None and core.edad_entera(valor) != valor]
    return f" [edad actuarial: {', '.join(notas)}]" if notas else ""


CODIGO_ERROR_TASA = 2
CODIGO_ERROR_GRUPO = 3


def main(argv: list[str] | None = None) -> int:
    """Ejecuta la CLI. Sin tasa determinable (o con vector inexistente) escribe
    el mensaje de la API en stderr y devuelve :data:`CODIGO_ERROR_TASA`; un
    grupo familiar que la norma no admite (articulo 58) devuelve
    :data:`CODIGO_ERROR_GRUPO`. Las advertencias de la API (p.ej. FAJ
    derogado) se escriben en stderr y no cambian el codigo de salida."""
    args = construir_parser().parse_args(argv)
    try:
        with warnings.catch_warnings(record=True) as avisos:
            warnings.simplefilter("always")
            codigo = _ejecutar(args)
    except _grupo.ErrorGrupoFamiliar as e:
        print(f"cnu {args.comando}: error: {e}", file=sys.stderr)
        return CODIGO_ERROR_GRUPO
    except (ValueError, FileNotFoundError) as e:
        print(f"cnu {args.comando}: error: {e}", file=sys.stderr)
        print("Entregue la tasa con --rp (TITRP), --rv o --agno-vector, o un --fsiniestro anterior a 2014.",
              file=sys.stderr)
        return CODIGO_ERROR_TASA
    # Las advertencias (p.ej. FAJ derogado) van a stderr sin cambiar el codigo de salida.
    for aviso in avisos:
        print(f"cnu {args.comando}: advertencia: {aviso.message}", file=sys.stderr)
    return codigo


def _ejecutar(args) -> int:
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

    # Regla unica de tasa (la misma de la API), resuelta antes de imprimir
    # nada: sin tasa determinable o con vector inexistente se falla con stdout
    # vacio. La descripcion (tabla y tasa efectivas) va en la primera linea.
    core.tasas_por_periodo(args.agno_vector, getattr(args, "rv", None), _nan_a_none(args.rp),
                           args.dir_vectores, args.fsiniestro)
    if c == "afil":
        print(core.describir("soltero sin hijos", args.tabla, None, args.agno_vector, args.agno_actual,
                             args.rv, args.rp, args.fsiniestro, mujer=args.mujer, dir_tablas=args.dir_tablas)
              + _nota_edades(afiliado=args.x))
        v = core.cnu_afiliado(args.x, args.mujer, args.tabla, rv=args.rv, rp=args.rp, pasos=args.pasos, **comunes)
        print(f"{v:9.6f}")
    elif c == "conyuge":
        print(core.describir(etiqueta_conyuge(args.conviviente), args.tabla, args.tabla_benef, args.agno_vector,
                             args.agno_actual, args.rv, args.rp, args.fsiniestro,
                             mujer=args.cot_mujer, benef_mujer=not args.cony_hombre, dir_tablas=args.dir_tablas)
              + _nota_edades(afiliado=args.x, conyuge=args.y))
        v = core.cnu_conyuge(args.x, args.y, args.cot_mujer, not args.cony_hombre, args.tabla, args.tabla_benef,
                             rv=args.rv, rp=args.rp, pasos=args.pasos, conviviente=args.conviviente, **comunes)
        print(f"{v:9.6f}")
    elif c == "sobrev":
        print(core.describir("sobrevivencia de " + etiqueta_conyuge(args.conviviente), None, args.tabla_benef,
                             args.agno_vector, args.agno_actual, args.rv, args.rp, args.fsiniestro,
                             benef_mujer=args.mujer, dir_tablas=args.dir_tablas)
              + _nota_edades(conyuge=args.y))
        v = core.cnu_sobrevivencia_conyuge(args.y, args.mujer, args.tabla_benef, rv=args.rv, rp=args.rp,
                                           pasos=args.pasos, conviviente=args.conviviente, **comunes)
        print(f"{v:9.6f}")
    elif c == "conyuge-ch":
        print(core.describir(etiqueta_conyuge(args.conviviente, True, args.hijo_invalido), args.tabla,
                             args.tabla_benef, args.agno_vector, args.agno_actual, args.rv, args.rp,
                             args.fsiniestro, mujer=args.cot_mujer, benef_mujer=not args.cony_hombre,
                             dir_tablas=args.dir_tablas)
              + _nota_edades(afiliado=args.x, conyuge=args.y, hijo=args.h))
        v = core.cnu_conyuge_con_hijos(args.x, args.y, args.h, args.cot_mujer, not args.cony_hombre,
                                       args.hijo_invalido, args.tabla, args.tabla_benef, rv=args.rv, rp=args.rp,
                                       pasos=args.pasos, conviviente=args.conviviente, **comunes)
        print(f"{v:9.6f}")
    elif c == "sobrev-conyuge-ch":
        print(core.describir("sobrevivencia de " + etiqueta_conyuge(args.conviviente, True, args.hijo_invalido),
                             None, args.tabla_benef, args.agno_vector, args.agno_actual, args.rv, args.rp,
                             args.fsiniestro, benef_mujer=args.mujer, dir_tablas=args.dir_tablas)
              + _nota_edades(conyuge=args.y, hijo=args.h))
        v = core.cnu_sobrevivencia_conyuge_con_hijos(args.y, args.h, args.mujer, args.hijo_invalido,
                                                     args.tabla_benef, rv=args.rv, rp=args.rp, pasos=args.pasos,
                                                     conviviente=args.conviviente, **comunes)
        print(f"{v:9.6f}")
    elif c == "hijo":
        print(core.describir("hijo no inválido 15%", args.tabla, args.tabla_benef, args.agno_vector,
                             args.agno_actual, args.rv, args.rp, args.fsiniestro,
                             mujer=args.cot_mujer, benef_mujer=args.hijo_mujer, dir_tablas=args.dir_tablas)
              + _nota_edades(afiliado=args.x, hijo=args.h))
        v = core.cnu_hijo(args.x, args.h, args.cot_mujer, args.hijo_mujer, args.tabla, args.tabla_benef,
                          rv=args.rv, rp=args.rp, pasos=args.pasos, **comunes)
        print(f"{v:9.6f}")
    elif c == "sobrev-hijo":
        print(core.describir("sobrevivencia de hijo no inválido 15%", None, args.tabla_benef, args.agno_vector,
                             args.agno_actual, args.rv, args.rp, args.fsiniestro,
                             benef_mujer=args.mujer, dir_tablas=args.dir_tablas)
              + _nota_edades(hijo=args.h))
        v = core.cnu_sobrevivencia_hijo(args.h, args.mujer, args.tabla_benef, rv=args.rv, rp=args.rp,
                                        pasos=args.pasos, **comunes)
        print(f"{v:9.6f}")
    elif c == "hijo-inv":
        print(core.describir(etiqueta_hijo_invalido(args.parcial), args.tabla, args.tabla_benef, args.agno_vector,
                             args.agno_actual, args.rv, args.rp, args.fsiniestro, mujer=args.cot_mujer,
                             benef_mujer=args.hijo_mujer, dir_tablas=args.dir_tablas, rol_benef=core.ROL_INVALIDO)
              + _nota_edades(afiliado=args.x, hijo=args.h))
        v = core.cnu_hijo_invalido(args.x, args.h, args.cot_mujer, args.hijo_mujer, args.parcial, args.tabla,
                                   args.tabla_benef, rv=args.rv, rp=args.rp, pasos=args.pasos, **comunes)
        print(f"{v:9.6f}")
    elif c == "sobrev-hijo-inv":
        print(core.describir("sobrevivencia de " + etiqueta_hijo_invalido(args.parcial), None, args.tabla_benef,
                             args.agno_vector, args.agno_actual, args.rv, args.rp, args.fsiniestro,
                             benef_mujer=args.mujer, dir_tablas=args.dir_tablas, rol_benef=core.ROL_INVALIDO)
              + _nota_edades(hijo=args.h))
        v = core.cnu_sobrevivencia_hijo_invalido(args.h, args.mujer, args.parcial, args.tabla_benef, rv=args.rv,
                                                 rp=args.rp, pasos=args.pasos, **comunes)
        print(f"{v:9.6f}")
    elif c == "madre-padre":
        print(core.describir(etiqueta_madre_padre(not args.padre, args.h, args.hijo_invalido), args.tabla,
                             args.tabla_benef, args.agno_vector, args.agno_actual, args.rv, args.rp,
                             args.fsiniestro, mujer=args.cot_mujer, benef_mujer=not args.padre,
                             dir_tablas=args.dir_tablas)
              + _nota_edades(afiliado=args.x, **{"madre o padre": args.u}, hijo=args.h))
        v = core.cnu_madre_padre(args.x, args.u, args.h, args.cot_mujer, not args.padre, args.hijo_invalido,
                                 args.tabla, args.tabla_benef, rv=args.rv, rp=args.rp, pasos=args.pasos, **comunes)
        print(f"{v:9.6f}")
    elif c == "sobrev-madre-padre":
        print(core.describir("sobrevivencia de " + etiqueta_madre_padre(not args.padre, args.h, args.hijo_invalido),
                             None, args.tabla_benef, args.agno_vector, args.agno_actual, args.rv, args.rp,
                             args.fsiniestro, benef_mujer=not args.padre, dir_tablas=args.dir_tablas)
              + _nota_edades(**{"madre o padre": args.u}, hijo=args.h))
        v = core.cnu_sobrevivencia_madre_padre(args.u, args.h, not args.padre, args.hijo_invalido, args.tabla_benef,
                                               rv=args.rv, rp=args.rp, pasos=args.pasos, **comunes)
        print(f"{v:9.6f}")
    elif c == "padres":
        print(core.describir(etiqueta_padres(not args.padre), args.tabla, args.tabla_benef, args.agno_vector,
                             args.agno_actual, args.rv, args.rp, args.fsiniestro, mujer=args.cot_mujer,
                             benef_mujer=not args.padre, dir_tablas=args.dir_tablas)
              + _nota_edades(afiliado=args.x, **{"madre" if not args.padre else "padre": args.m}))
        v = core.cnu_padres(args.x, args.m, args.cot_mujer, not args.padre, args.tabla, args.tabla_benef,
                            rv=args.rv, rp=args.rp, pasos=args.pasos, **comunes)
        print(f"{v:9.6f}")
    elif c == "sobrev-padres":
        print(core.describir("sobrevivencia de " + etiqueta_padres(not args.padre, "del causante"), None,
                             args.tabla_benef, args.agno_vector, args.agno_actual, args.rv, args.rp,
                             args.fsiniestro, benef_mujer=not args.padre, dir_tablas=args.dir_tablas)
              + _nota_edades(**{"madre" if not args.padre else "padre": args.m}))
        v = core.cnu_sobrevivencia_padres(args.m, not args.padre, args.tabla_benef, rv=args.rv, rp=args.rp,
                                          pasos=args.pasos, **comunes)
        print(f"{v:9.6f}")
    elif c == "grupo":
        afiliado = None if args.afiliado is None else _grupo.Afiliado(args.afiliado[0], bool(args.afiliado[1]))
        beneficiarios = _beneficiarios_cli(args)
        r = _grupo.cnu_grupo_familiar(afiliado, beneficiarios, args.uf, args.tabla, args.tabla_benef,
                                      rv=args.rv, rp=args.rp, **comunes)
        edades = {} if afiliado is None else {"afiliado": afiliado.edad}
        for i, b in enumerate(beneficiarios, 1):
            edades[f"{b.tipo.replace('_', ' ')} {i}"] = b.edad
        print(r.descripcion + _nota_edades(**edades))
        if args.pasos:  # la descripcion va primero; el detalle periodo a periodo se imprime al recalcular
            r = _grupo.cnu_grupo_familiar(afiliado, beneficiarios, args.uf, args.tabla, args.tabla_benef,
                                          rv=args.rv, rp=args.rp, pasos=True, **comunes)
        for comp in r.componentes:
            print(f"  {comp.etiqueta:<44s}{comp.cnu:12.6f}")
        print(f"  {'total':<44s}{r.total:12.6f}")
    elif c == "faj":
        rp = _nan_a_none(args.rp)
        quien = "afiliado soltero" if args.y is None else "afiliado con conyuge"
        tasa = _etiqueta_tasa(None, rp, args.agno_vector, args.fsiniestro)
        v = _faj.faj_afiliado(
            args.x, args.y, args.cot_mujer, not args.cony_hombre, args.tabla, args.tabla_benef,
            rp=rp, edad_maxima=args.edad_maxima, saldo=args.saldo, pcent=args.pcent,
            rp0=args.rp0, criter=args.criter, maxiter=args.maxiter, **comunes,
        )
        print(f"FAJ para {quien}, {tasa}" + _nota_edades(afiliado=args.x, conyuge=args.y))
        print(f"{v:9.6f}")
    elif c == "proy":
        r = proyeccion.proyectar_pension(
            args.x, args.y, args.saldo, args.cot_mujer, not args.cony_hombre, args.tabla, args.tabla_benef,
            rp=_nan_a_none(args.rp), faj=args.faj, banda=args.banda, edad_maxima=args.edad_maxima,
            pcent=args.pcent, rp0=args.rp0, criter=args.criter, maxiter=args.maxiter, **comunes,
        )
        cols = r.columnas()
        if args.csv:
            w = csv.writer(sys.stdout)
            w.writerow(cols)
            w.writerows(zip(*cols.values()))
        else:
            print(r.descripcion + _nota_edades(afiliado=args.x, conyuge=args.y))
            print("".join(f"{k:>12}" for k in cols))
            for fila in zip(*cols.values()):
                print("".join(f"{v:12.6f}" for v in fila))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

# cnu : Cálculo del Capital Necesario Unitario (CNU) en Python

Paquete Python para el cálculo de Capitales Necesarios Unitarios (CNU),
utilizados en el cálculo de pensiones del sistema chileno. Es la conversión a
Python del módulo de Stata/Mata `cnu` de George G. Vega Yon (Superintendencia
de Pensiones), cuyo código original se conserva en `ado/` y `man/`.

Implementa las fórmulas de CNU para pensión de vejez de afiliado y de cónyuge
sin hijos, para pensión de sobrevivencia de cónyuge sin hijos, la proyección
de pensión en Retiro Programado y el Factor de Ajuste (FAJ, derogado desde
2022 y conservado solo para cálculos históricos), con todas las tablas de
mortalidad normativas desde 1985 hasta las TM2020 vigentes. La sección
[Estado normativo](#estado-normativo) resume qué está alineado con el
Compendio de Normas de la Superintendencia de Pensiones (SP) y qué debe
entregar el usuario.

## Instalación

Requiere Python 3.12 o superior. Con [uv](https://docs.astral.sh/uv/):

```
uv sync            # crea el entorno e instala numpy
uv run pytest      # corre los tests
```

O con pip: `pip install .`

## Uso desde Python

Sin indicar tabla, el paquete usa la tabla de mortalidad **vigente** para el
rol (afiliado o beneficiario), el sexo y la fecha de cálculo. En 2026 son las
TM2020: `cb2020h` para hombres, `rv2020m` para afiliadas y `b2020m` para
beneficiarias.

```python
import cnu

# CNU de afiliado de 65 años en 2026 (tabla cb2020h), tasa única de RP 3%
cnu.cnu_afiliado(65, rp=0.03, agno_actual=2026)                   # 15.456439
cnu.cnu_afiliado(60, mujer=True, rp=0.03, agno_actual=2026)       # 19.764704  (rv2020m)

# Renta vitalicia, o vector de tasas de RP explícito
cnu.cnu_afiliado(67, rv=0.032, agno_actual=2026)
cnu.cnu_afiliado(65, agno_vector=2013, agno_actual=2026)          # 14.042741  (vector 2013)

# CNU del cónyuge (se suma al del afiliado para obtener el CNU total)
cnu.cnu_conyuge(65, 63, cony_mujer=True, rp=0.03, agno_actual=2026)   # 2.493278  (cb2020h, b2020m)

# CNU de sobrevivencia para cónyuge sin hijos
cnu.cnu_sobrevivencia_conyuge(63, mujer=True, rp=0.03, agno_actual=2026)  # 10.674379  (b2020m)

# Hijo no inválido (15%, con derecho hasta los 24 años): afiliado de 65 e hijo de 10
cnu.cnu_hijo(65, 10, rp=0.03, agno_actual=2026)                    # 0.135662  (cb2020h, cb2020h)
cnu.cnu_hijo(65, 30, rp=0.03, agno_actual=2026)                    # 0.0  (24 años o más)
cnu.cnu_sobrevivencia_hijo(10, mujer=True, rp=0.03, agno_actual=2026)  # 1.720195  (b2020m)

# Hijo inválido (tabla de inválidos, sin edad límite): total 15% vitalicio; parcial 15% hasta los 24 años y 11% después
cnu.cnu_hijo_invalido(65, 30, rp=0.03, agno_actual=2026)                  # 1.257455  (cb2020h, mi2020h)
cnu.cnu_hijo_invalido(65, 21, hijo_mujer=True, parcial=True, rp=0.03, agno_actual=2026)  # 1.259397  (cb2020h, mi2020m)
cnu.cnu_sobrevivencia_hijo_invalido(21, mujer=True, rp=0.03, agno_actual=2026)           # 3.939510  (mi2020m)

# Cónyuge con hijos con derecho a pensión: 50% hasta los 24 años del hijo menor (aquí de 10) y 60% después;
# con algún hijo inválido, 50% vitalicio. Con el hijo menor de 24 o más coincide con el cónyuge sin hijos
cnu.cnu_conyuge_con_hijos(65, 63, 10, rp=0.03, agno_actual=2026)                      # 2.409035  (cb2020h, b2020m)
cnu.cnu_conyuge_con_hijos(65, 63, 10, hijo_invalido=True, rp=0.03, agno_actual=2026)  # 2.077732
cnu.cnu_sobrevivencia_conyuge_con_hijos(63, 10, mujer=True, rp=0.03, agno_actual=2026)  # 9.578224  (b2020m)

# Conviviente civil: las funciones del cónyuge con conviviente=True (misma fórmula, mismo valor)
cnu.cnu_conyuge(65, 63, conviviente=True, rp=0.03, agno_actual=2026)   # 2.493278

# Factor de ajuste (derogado desde el 1-2-2022: con fecha posterior emite AdvertenciaCNU)
cnu.faj_afiliado(65, rp=0.03, agno_vector=2013, agno_actual=2026)      # 0.037205
cnu.faj_afiliado(65, 62, rp=0.03, agno_vector=2013, agno_actual=2026)  # 0.004659

# Proyección de pensión en retiro programado (con o sin FAJ; con faj=True, misma advertencia)
p = cnu.proyectar_pension(65, saldo=1000, rp=0.03, agno_actual=2026)
p.edad, p.saldo, p.pension                       # p.pension[0] = 64.6979
p = cnu.proyectar_pension(65, saldo=1000, rp=0.03, faj=True, agno_actual=2026)
p.edad, p.saldo, p.pension, p.faj, p.saldo_faj   # p.pension[0] = 63.2245, p.faj = 0.022775
p.to_dataframe()        # requiere pandas

# Con fecha del siniestro, la tabla es la vigente a esa fecha
cnu.cnu_afiliado(65, fsiniestro=20230630, rp=0.03, agno_actual=2023)   # 15.063535  (cb2014h)
cnu.cnu_afiliado(65, fsiniestro=20230701, rp=0.03, agno_actual=2023)   # 15.320124  (cb2020h)

# Qué tabla y qué tasa se usaron
cnu.describir("soltero sin hijos", "vigente", rp=0.03, agno_actual=2026)
# 'CNU RP para soltero sin hijos (tabla cb2020h), tasa 3% en el año 2026'

# Edad actuarial: la edad exacta redondeada al entero más cercano (seis meses o más suben)
cnu.edad_actuarial(19600915, 20260315)                   # 66  (acepta YYYYMMDD o datetime.date)
cnu.cnu_afiliado(65.7, rp=0.0345, agno_actual=2026)      # 14.322867, igual que con 66
```

Si `agno_actual` no se entrega se usa el año del sistema.

Las edades se interpretan como **edad actuarial**, como exige el Compendio:
una edad decimal se redondea al entero más cercano con el medio hacia arriba
(`65.4` → 65, `65.5` → 66) en todas las funciones, antes de validar el rango
de 20 a 110 años. `cnu.edad_actuarial(fecha_nacimiento, fecha_calculo)` la
obtiene a partir de dos fechas.

La tasa de descuento debe ser explícita: `rv` (renta vitalicia), `rp` (tasa
única de retiro programado, la TITRP que publica la SP desde 2014) o
`agno_vector` (vector de tasas de ese año). Sin ninguna de ellas, solo un
`fsiniestro` anterior al 1 de enero de 2014 (`cnu.INICIO_TITRP`) usa el vector
del año del siniestro; en cualquier otro caso el cálculo falla con un
`ValueError` que lo explica.

### Ejemplos históricos

Los valores de referencia de la ayuda de Stata se obtenían con `rv2009` y
`b2006`. Se reproducen indicando el año de cálculo (la tabla vigente en
2011-2014 es `rv2009`/`b2006`) o la tabla explícita:

```python
cnu.cnu_afiliado(65, agno_vector=2013, agno_actual=2013)        # 13.016877
cnu.cnu_afiliado(65, tabla="rv2009", agno_vector=2013, agno_actual=2013)   # idem
cnu.cnu_afiliado(65, rp=0.0366, agno_actual=2014)               # 13.377535
cnu.cnu_conyuge(65, 63, cony_mujer=True, agno_vector=2011, agno_actual=2011)  # 2.231859
cnu.faj_afiliado(65, rp=0.03, agno_vector=2013, agno_actual=2014)      # 0.066178
cnu.faj_afiliado(65, 62, rp=0.03, agno_vector=2013, agno_actual=2014)  # 0.013094
cnu.cnu_afiliado(65, fsiniestro=20130101, agno_actual=2013)     # 13.016877  (vector 2013 por el siniestro)
```

Una tabla explícita se respeta aunque no sea la vigente:
`cnu.cnu_afiliado(65, tabla="rv2009", agno_actual=2026)` usa `rv2009h`.

### Versiones vectoriales

Las funciones con sufijo `_vec` equivalen a los comandos de Stata que operan
sobre variables (`cnu_afil`, `cnu_cnyg_s_h`, `cnu_sobr_cnyg_s_h`, `cnu_faj`);
`cnu_hijo_vec`, `cnu_sobrevivencia_hijo_vec`, `cnu_hijo_invalido_vec`,
`cnu_sobrevivencia_hijo_invalido_vec`, `cnu_conyuge_con_hijos_vec` y
`cnu_sobrevivencia_conyuge_con_hijos_vec` no tienen comando equivalente.
Cada argumento puede ser un escalar o un arreglo con un valor por fila. La
tabla `"vigente"` se resuelve fila a fila con el sexo, el `agno_actual` y el
`fsiniestro` de cada observación.

```python
import numpy as np
edades = np.array([55, 65, 75])
cnu.cnu_afiliado_vec(edades, mujer=[0, 1, 0], rp=0.03, agno_actual=2026)
cnu.cnu_afiliado_vec(edades, fsiniestro=[20130101, 20200101, 20240101], rp=0.03)   # rv2009, cb2014, cb2020
cnu.cnu_conyuge_vec(edades, [53, 63, 73], cony_mujer=True, rp=[0.03, np.nan, 0.03])  # fila 1 sin tasa -> nan
cnu.cnu_hijo_vec(edades, [3, 12, 25], hijo_mujer=[0, 1, 0], rp=0.03)                # fila 2: 0 (24 años o más)
cnu.cnu_hijo_invalido_vec(edades, [3, 12, 25], parcial=[0, 1, 1], rp=0.03)          # tabla mi, sin edad límite
cnu.cnu_conyuge_con_hijos_vec(edades, [53, 63, 73], [3, 12, 25], cony_mujer=True, rp=0.03)  # fila 2: como sin hijos
cnu.faj_afiliado_vec(edades, rp=0.03)
```

La tasa se resuelve fila a fila con la misma regla que las funciones
escalares (`rv`, `rp`, `agno_vector` o `fsiniestro` anterior a 2014 de cada
observación). Las filas con edad fuera de [20, 110] (negativa en el caso de
los hijos, que se calculan desde los 0 años), sin tasa determinable o con
vector de tasas inexistente quedan en `nan` y se emite una advertencia
`cnu.AdvertenciaCNU` con los índices y el motivo.

### Opciones comunes

| Argumento | Descripción |
|---|---|
| `tabla` | Tabla de mortalidad del afiliado: `"vigente"` (por defecto) o un nombre explícito como `"rv2009"`, `"cb2020"`. |
| `tabla_benef` | Tabla del beneficiario: `"vigente"` (por defecto) o un nombre explícito como `"b2006"`, `"b2020"` (`"mi2020"` para el hijo inválido, cuyo rol es el de inválido). |
| `mujer`, `cot_mujer`, `cony_mujer`, `hijo_mujer` | Sexo del afiliado, cónyuge o hijo; determina la tabla (`cb` para hombres desde 2016). |
| `parcial` | Grado de invalidez del hijo inválido: `False` (por defecto) total, 15% vitalicio; `True` parcial, 15% hasta los 24 años y 11% después. |
| `h` (cónyuge con hijos) | Edad del hijo menor con derecho a pensión: fija el tramo al 50% (hasta que cumpla 24 años) y el tramo al 60% desde entonces. |
| `hijo_invalido` | `True` si algún hijo con derecho a pensión del cónyuge es inválido: 50% vitalicio (la edad `h` no interviene). |
| `conviviente` | `True` si el beneficiario de las funciones del cónyuge es conviviente civil (Ley N° 20.830): misma fórmula y mismo valor; documenta el rol. |
| `agno_vector` | Año del vector de tasas para Retiro Programado. Sin él, solo un `fsiniestro` anterior a 2014 usa por defecto el vector de su año. |
| `agno_actual` | Año de cálculo; ajusta las tablas por mejoramiento y, sin `fsiniestro`, fija la tabla vigente al 31 de diciembre de ese año (por defecto, el año actual). |
| `rv` | Tasa de renta vitalicia. Si se entrega, el CNU es de RV. |
| `rp` | Tasa única de retiro programado (TITRP). Obligatoria desde 2014 si no se entrega `rv` ni `agno_vector`. |
| `fsiniestro` | Fecha del siniestro `YYYYMMDD`; asigna la tabla vigente a esa fecha. |
| `pasos` | Imprime el cálculo periodo a periodo, indicando la tabla resuelta. |
| `dir_tablas`, `dir_vectores` | Directorios con tablas o vectores propios. |

## Línea de comandos

Los subcomandos aceptan las mismas opciones (`--tabla`, `--tabla-benef`,
`--agno-actual`, `--fsiniestro`, ...), con `vigente` como tabla por defecto y
la misma regla de tasa que la API: sin `--rp`, `--rv`, `--agno-vector` ni un
`--fsiniestro` anterior a 2014 el comando termina con un mensaje en stderr y
código de salida 2. La primera línea de la salida indica la tabla y la tasa
efectivamente usadas (`tasa 3.45%` o `vector 2013`).

```
cnu afil 65 --rp 0.03 --agno-actual 2026
cnu afil 65.7 --rp 0.0345 --agno-actual 2026    # edad actuarial 66, indicada en la primera línea
cnu afil 65 --fsiniestro 20240315 --rp 0.03
cnu afil 65 --mujer --rp 0.03 --pasos
cnu afil 65 --tabla rv2009 --agno-vector 2013 --agno-actual 2013
cnu conyuge 65 63 --rp 0.03 --agno-actual 2026
cnu sobrev 63 --mujer --rp 0.03
cnu hijo 65 10 --rp 0.03 --agno-actual 2026     # hijo no inválido 15% (pensión de vejez o invalidez)
cnu sobrev-hijo 10 --mujer --rp 0.03            # sobrevivencia de hijo no inválido 15%
cnu hijo-inv 65 30 --rp 0.03 --agno-actual 2026 # hijo inválido total 15% (tabla mi, sin edad límite)
cnu hijo-inv 65 21 --parcial --hijo-mujer --rp 0.03   # hijo inválido parcial 15%/11%
cnu sobrev-hijo-inv 21 --mujer --rp 0.03        # sobrevivencia de hijo inválido total 15%
cnu conyuge-ch 65 63 10 --rp 0.03 --agno-actual 2026  # cónyuge con hijos 50%/60% (hijo menor de 10 años)
cnu conyuge-ch 65 63 10 --hijo-invalido --rp 0.03     # cónyuge con hijo inválido 50%
cnu sobrev-conyuge-ch 63 10 --mujer --rp 0.03         # sobrevivencia de cónyuge con hijos 50%/60%
cnu conyuge 65 63 --conviviente --rp 0.03             # conviviente civil (mismo valor que el cónyuge)
cnu faj 65 62 --rp 0.03 --agno-vector 2013
cnu proy 65 --faj --csv --rp 0.03 > trayectoria.csv
cnu tablas
```

```
$ cnu afil 65 --fsiniestro 20240315 --rp 0.03
CNU RP para soltero sin hijos (tabla cb2020h), tasa 3% en el año 2026
15.456439
$ cnu hijo 65 10 --rp 0.03 --agno-actual 2026
CNU RP para hijo no inválido 15% (tablas cb2020h cb2020h), tasa 3% en el año 2026
 0.135662
$ cnu hijo-inv 65 30 --rp 0.03 --agno-actual 2026
CNU RP para hijo inválido total 15% (tablas cb2020h mi2020h), tasa 3% en el año 2026
 1.257455
$ cnu conyuge-ch 65 63 10 --rp 0.03 --agno-actual 2026
CNU RP para cónyuge con hijos 50%/60% (tablas cb2020h b2020m), tasa 3% en el año 2026
 2.409035
```

## Estado normativo

### Alineado con el Compendio de Normas

* **Fórmulas del CNU** del Anexo N° 7 del Libro III: afiliado, cónyuge sin
  hijos (pensión de vejez) y sobrevivencia de cónyuge sin hijos, con el ajuste
  de 11/24 por pago mensual, tal como las rutinas Mata originales.
* **Tablas de mortalidad y vigencias** del Título X del Libro III: desde las
  tablas de 1985 hasta las TM2020, seleccionadas automáticamente por rol,
  sexo y fecha del siniestro (o fin del año de cálculo); factores de
  mejoramiento del Anexo N° 9, históricos y bidimensionales 2021-2036.
* **Tasa de descuento**: desde el 1 de enero de 2014 rige la tasa de interés
  técnico del retiro programado (TITRP) que fija la SP, por lo que el paquete
  no tiene vector de tasas por defecto; solo un siniestro anterior a esa fecha
  usa el vector del año del siniestro.
* **Edad actuarial**, como la define el Capítulo III (Retiro Programado) de
  la Letra F del Título I del Libro III: la edad a la fecha de cálculo
  redondeada al entero más cercano, subiendo desde los seis meses.

### Lo que debe entregar el usuario

* **La TITRP vigente.** La SP la publica mediante circular en la página
  [Tasas de interés para el cálculo de los retiros programados y las rentas
  temporales](https://www.spensiones.cl/apps/tasas/tasdescto.php); a
  septiembre de 2026 rige 3,45% desde julio de 2026 (Circular N° 2.417). En
  cada recálculo trimestral se pasa la tasa del trimestre como `rp` (o `--rp`
  en la CLI); para renta vitalicia, la tasa de la póliza en `rv`.

  ```python
  cnu.cnu_afiliado(65, rp=0.0345, agno_actual=2026)   # 14.755007
  ```

* **La edad actuarial** del afiliado y de los beneficiarios a la fecha de
  cálculo: `cnu.edad_actuarial(fecha_nacimiento, fecha_calculo)` la obtiene a
  partir de dos fechas (`YYYYMMDD` o `datetime.date`), y toda función acepta
  edades decimales que redondea con la misma regla.
* **El año de cálculo** (`agno_actual`) o la **fecha del siniestro**
  (`fsiniestro`), que determinan la tabla vigente y el mejoramiento.

### Factor de Ajuste derogado

La Ley N° 21.419 eliminó el Factor de Ajuste del retiro programado a contar
del 1 de febrero de 2022, y el Capítulo V de la Letra F del Título I del
Libro III quedó derogado. `faj_afiliado`, `faj_afiliado_vec` y
`proyectar_pension(faj=True)` se conservan para reproducir cálculos
históricos: con fecha de cálculo igual o posterior a `cnu.DEROGACION_FAJ`
(20220201) emiten una `AdvertenciaCNU` y devuelven el valor de todos modos.

### Beneficiarios cubiertos y pendientes

| Cubierto | Pendiente |
|---|---|
| Afiliado (`cnu_afiliado`) | Hijos sin cónyuge ni madre o padre con derecho a pensión (letras 1.f, 1.g, 2.g y 2.h, porcentaje con 0,5/n) |
| Cónyuge sin hijos, pensión de vejez (`cnu_conyuge`, letra 2.b del Anexo N° 7) | Conviviente civil sin hijos comunes que concurre con hijos del causante (letras 1.m, 1.o, 2.n y 2.p, 15% mientras haya hijos con derecho) |
| Sobrevivencia de cónyuge sin hijos (`cnu_sobrevivencia_conyuge`, letra 1.a) | Madre o padre de hijos de filiación no matrimonial |
| Cónyuge con hijos con derecho a pensión: 50% hasta los 24 años del hijo menor y 60% después, o 50% vitalicio con algún hijo inválido, pensión de vejez o invalidez (`cnu_conyuge_con_hijos`, letras 2.c y 2.d) | Padres del afiliado |
| Sobrevivencia de cónyuge con hijos (`cnu_sobrevivencia_conyuge_con_hijos`, letras 1.b y 1.c) | Cuota mortuoria |
| Conviviente civil sin hijos o con hijos comunes (`conviviente=True` en las funciones del cónyuge; letras 1.l, 1.n, 1.p, 2.m, 2.o y 2.q, misma fórmula con `a` en lugar de `y`) | |
| Hijo no inválido, 15% hasta los 24 años, pensión de vejez o invalidez (`cnu_hijo`, letra 2.e) | |
| Sobrevivencia de hijo no inválido (`cnu_sobrevivencia_hijo`, letra 1.d) | |
| Hijo inválido total (15% vitalicio) o parcial (15% hasta los 24 años y 11% después), con tabla de inválidos, pensión de vejez o invalidez (`cnu_hijo_invalido`, letra 2.f) | |
| Sobrevivencia de hijo inválido total o parcial (`cnu_sobrevivencia_hijo_invalido`, letra 1.e) | |

Las funciones del hijo reciben su edad desde los 0 años; las del hijo no
inválido devuelven 0 desde los 24 y las del hijo inválido no tienen edad
límite. Las del cónyuge con hijos reciben la edad del hijo menor con derecho
(`h`) y un indicador de hijo inválido; con `h` de 24 o más devuelven
exactamente el valor del cónyuge sin hijos. La elegibilidad (por ejemplo, la
calidad de estudiante entre los 18 y los 24 años, la invalidez declarada y su
grado, o la existencia de la unión civil) es un dato de entrada que el
paquete no valida.

### Ley N° 21.735

La Ley N° 21.735 (marzo de 2025) introdujo una banda de variación máxima del
10% para los recálculos trimestrales de las pensiones en retiro programado
(desde el 1 de septiembre de 2025) y la Compensación por Diferencias de
Expectativa de Vida (CEV), regulada en la Letra C del Título XIX del Libro
III. Ninguna de las dos modifica la fórmula del CNU: la banda actúa sobre la
pensión resultante y la CEV es un beneficio adicional. No están
implementadas en este paquete.

## Tablas de mortalidad

### Tablas incluidas y vigencias

Las tablas viven en `src/cnu/data` como `cnu_tabmor_[tipo][año][género].csv`.
El tipo es `rv` (afiliado), `b` (beneficiario), `mi` (inválido) o `cb`
(combinada: hombres afiliados y beneficiarios, desde 2014); el género es `h` o
`m`. `cnu tablas` o `cnu.tablas_disponibles()` las listan.

| Tablas | Afiliado H | Afiliada M | Benef. H | Benef. M | Inválido H/M | Factores |
|---|---|---|---|---|---|---|
| 1985 | rv1985h | rv1985m | b1985h | b1985m | mi1985h/m | histórico |
| 2004 | rv2004h | rv2004m | | | | histórico |
| 2006 | | | b2006h | b2006m | mi2006h/m | histórico |
| 2009 | rv2009h | rv2009m | | | | histórico |
| TM2014 | cb2014h | rv2014m | cb2014h | b2014m | mi2014h/m | histórico |
| TM2020 | cb2020h | rv2020m | cb2020h | b2020m | mi2020h/m | bidimensional 2021-2036 |

Cada tabla rige según la fecha del siniestro (o de la pensión), el rol y el
sexo:

| Fecha | Afiliado H | Afiliada M | Benef. H | Benef. M | Inválido H/M |
|---|---|---|---|---|---|
| hasta 31-01-2005 | rv1985 | rv1985 | b1985 | b1985 | mi1985 |
| 01-02-2005 a 31-01-2008 | rv2004 | rv2004 | b1985 | b1985 | mi1985 |
| 01-02-2008 a 30-06-2010 | rv2004 | rv2004 | b2006 | b2006 | mi2006 |
| 01-07-2010 a 30-06-2016 | rv2009 | rv2009 | b2006 | b2006 | mi2006 |
| 01-07-2016 a 30-06-2023 | cb2014 | rv2014 | cb2014 | b2014 | mi2014 |
| desde 01-07-2023 | cb2020 | rv2020 | cb2020 | b2020 | mi2020 |

El selector `cnu.tabla_por_fecha(fecha, rol, genero)` devuelve el tipo y el
año para una fecha `YYYYMMDD`, un rol (`"rv"`, `"b"` o `"mi"`) y un sexo:

```python
cnu.tabla_por_fecha(20240101, "rv", "h")   # ('cb', 2020)
cnu.tabla_por_fecha(20240101, "rv", "m")   # ('rv', 2020)
cnu.tabla_por_fecha(20200101, "b", "h")    # ('cb', 2014)
cnu.tabla_mortalidad("vigente", cnu.ROL_AFILIADO, mujer=False, agno_actual=2026).nombre
# 'cnu_tabmor_cb2020h'
```

### Default `"vigente"` y convención de fin de año

`tabla` y `tabla_benef` valen `"vigente"` por defecto y se resuelven así:

* nombre explícito (`"rv2009"`, `"cb2020"`, ...): se usa tal cual; si además
  se entrega `fsiniestro`, la tabla se reasigna a la vigente a esa fecha;
* `"vigente"` con `fsiniestro`: la tabla vigente a la fecha del siniestro;
* `"vigente"` sin `fsiniestro`: **convención de fin de año**, la tabla
  vigente al 31 de diciembre de `agno_actual`. Así, `agno_actual=2016`
  resuelve a TM2014 y `agno_actual=2023` a TM2020; para un siniestro del
  primer semestre de esos años hay que entregar `fsiniestro`.

Las proyecciones y el FAJ resuelven las tablas una sola vez, al inicio de la
trayectoria, y las usan en todos los periodos. Pedir una combinación que no
existe (`cb2009`, `rv2020` para un hombre) produce un error que nombra la
combinación y remite a `tablas_disponibles`.

### Factores de mejoramiento

Cada tabla trae la probabilidad de muerte `qx` y factores de mejoramiento
`aa` que la reducen año a año. Para una persona de edad `x` en el año `a`,
cada edad futura `e` se evalúa en su propio año calendario `a + e - x`.

* Histórico (tablas 1985 a 2014, columnas `edad, qx, aa`):
  `qx(e) · (1 − aa(e))^(a − año_tabla + e − x)`.
* Bidimensional (TM2020, columnas `edad, qx, aa2021, ..., aa2036`), Anexo
  N° 9 de la SP: `qx(e) · ∏_{t=2021..a'} (1 − AA(e, min(t, 2036)))` con
  `a' = a + e − x`; si `a' ≤ 2020` se usa `qx` sin mejorar y desde 2037 se
  repite el factor de 2036.

```python
t = cnu.cargar_tabla_mortalidad("cb", 2020, "h")
t.bidimensional, t.agnos_aa[0], t.agnos_aa[-1]   # True, 2021, 2036
t.qx[65]                                          # 0.00887369
t.qx_mejorado(2022, 65)[65]                       # 0.0085260  (ejemplo oficial CB-H-2020)
```

### Tablas y vectores propios

* `cnu_tabmor_[tipo][año][género].csv` con columnas `edad, qx, aa` (histórica)
  o `edad, qx, aa2021, ..., aa2036` (bidimensional; los años se leen de la
  cabecera).
* `cnu_vec[año].csv` con columnas `t, tasa` (191 periodos). Incluidos: 2009 a
  2013.

Guárdelos en un directorio con esos nombres (en CSV o en el formato binario
original de Mata) y pase `dir_tablas` / `dir_vectores`. `guardar_tabla_mortalidad`
escribe ambos esquemas; para una matriz cruda de más de tres columnas hay que
indicar los años de los factores (`agnos_aa`), porque el binario de Mata no
guarda la cabecera:

```python
t = cnu.cargar_tabla_mortalidad("cb", 2020, "h")
cnu.guardar_tabla_mortalidad(t, 2020, "h", "cb", "mis_tablas")                       # CSV con cabecera aa2021..aa2036
cnu.guardar_tabla_mortalidad(t.como_matriz(), 2020, "h", "cb", "mis_tablas",
                             reemplazar=True, agnos_aa=range(2021, 2037))            # matriz cruda
cnu.guardar_tabla_mortalidad(cnu.cargar_tabla_mortalidad("rv", 2009, "h"), 2009, "h", "rv",
                             "mis_tablas", formato="mata")                           # histórica, binario Mata
cnu.cnu_afiliado(65, rp=0.03, agno_actual=2026, dir_tablas="mis_tablas")
```

`guardar_vector_tasas`, `leer_matriz_mata` y `escribir_matriz_mata` permiten
crear y convertir vectores y binarios.

Nota: en el módulo original las tablas se indexaban por número de fila (las
tablas `rv` empiezan en edad 1 y las `b`/`mi` en edad 0, lo que el código Mata
compensaba con distintos desplazamientos). En Python las tablas se indexan por
edad, lo que da resultados idénticos con las tablas incluidas y es robusto con
tablas propias.

## Módulo original de Stata

El módulo `cnu` de Stata, escrito fundamentalmente en Mata, se conserva en
`ado/` (código y binarios) y `man/` (nota técnica). Para instalarlo en Stata:

```
. net install cnu, from(https://cdn.rawgit.com/gvegayon/cnu/a31056b6) replace
. mata mata mlib query
```

## Referencias

* Superintendencia de Pensiones, Compendio de Normas del Sistema de Pensiones,
  Libro III, Título X (tablas de mortalidad) y Anexo N° 7 (capitales
  necesarios): https://www.spensiones.cl/portal/compendio/596/w3-propertyvalue-3483.html
* Superintendencia de Pensiones, Anexo N° 9: tablas TM2020 y fórmula de
  mejoramiento bidimensional: https://www.spensiones.cl/portal/compendio/596/fo-article-15659.pdf
* Superintendencia de Pensiones, Compendio, Libro III, Título I, Letra F,
  Capítulo III. Retiro Programado (cálculo, recálculo y edad actuarial):
  https://www.spensiones.cl/portal/compendio/596/w3-propertyvalue-3223.html
* Superintendencia de Pensiones, Compendio, Libro III, Título I, Letra F,
  Capítulo V. Aplicación de un Factor de Ajuste al Cálculo del Retiro
  Programado (derogado por la Ley N° 21.419 desde el 1 de febrero de 2022):
  https://www.spensiones.cl/portal/compendio/596/w3-propertyvalue-3225.html
* Superintendencia de Pensiones, Tasas de interés para el cálculo de los
  retiros programados y las rentas temporales (TITRP vigente por circular):
  https://www.spensiones.cl/apps/tasas/tasdescto.php
* Superintendencia de Pensiones, Nota Técnica N° 8: Tasa de Interés Técnica de
  Retiro Programado y Rentas Temporales y su efecto en el cálculo de las
  pensiones: https://www.spensiones.cl/portal/institucional/594/w3-article-15569.html
* Superintendencia de Pensiones, Nota Técnica N° 9 (noviembre de 2024):
  https://www.spensiones.cl/portal/institucional/594/articles-16151_recurso_1.pdf
* Superintendencia de Pensiones, Compendio, Libro III, Título XIX, Letra C.
  Compensación por Diferencias de Expectativa de Vida (Ley N° 21.735):
  https://www.spensiones.cl/portal/compendio/596/w3-propertyvalue-10821.html
* Superintendencia de Pensiones, Ley N° 21.735 (26 de marzo de 2025):
  https://www.spensiones.cl/portal/institucional/594/w3-article-16483.html
  y banda de variación máxima para el retiro programado:
  https://www.spensiones.cl/portal/institucional/594/w3-article-16568.html
* Comisión para el Mercado Financiero, NCG N° 495: publicación de las tablas
  TM2020: https://www.cmfchile.cl/portal/principal/623/w4-propertyvalue-48722.html

## Autores

* George G. Vega Yon, Superintendencia de Pensiones (módulo original en Stata/Mata).
* Francisco Javier Errandonea Terán (conversión a Python).

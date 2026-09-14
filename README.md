# cnu : Cálculo del Capital Necesario Unitario (CNU) en Python

Paquete Python para el cálculo de Capitales Necesarios Unitarios (CNU),
utilizados en el cálculo de pensiones del sistema chileno. Es la conversión a
Python del módulo de Stata/Mata `cnu` de George G. Vega Yon (Superintendencia
de Pensiones), cuyo código original se conserva en `ado/` y `man/`.

Implementa las fórmulas de CNU para pensión de vejez de afiliado y de cónyuge
sin hijos, para pensión de sobrevivencia de cónyuge sin hijos, la proyección
de pensión en Retiro Programado y el Factor de Ajuste (FAJ), con todas las
tablas de mortalidad normativas desde 1985 hasta las TM2020 vigentes.

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

# Factor de ajuste
cnu.faj_afiliado(65, rp=0.03, agno_vector=2013, agno_actual=2026)      # 0.037205
cnu.faj_afiliado(65, 62, rp=0.03, agno_vector=2013, agno_actual=2026)  # 0.004659

# Proyección de pensión en retiro programado (con o sin FAJ)
p = cnu.proyectar_pension(65, saldo=1000, rp=0.03, faj=True, agno_actual=2026)
p.edad, p.saldo, p.pension, p.faj, p.saldo_faj   # p.pension[0] = 63.2245, p.faj = 0.022775
p.to_dataframe()        # requiere pandas

# Con fecha del siniestro, la tabla es la vigente a esa fecha
cnu.cnu_afiliado(65, fsiniestro=20230630, rp=0.03, agno_actual=2023)   # 15.063535  (cb2014h)
cnu.cnu_afiliado(65, fsiniestro=20230701, rp=0.03, agno_actual=2023)   # 15.320124  (cb2020h)

# Qué tabla y qué tasa se usaron
cnu.describir("soltero sin hijos", "vigente", rp=0.03, agno_actual=2026)
# 'CNU RP para soltero sin hijos (tabla cb2020h), tasa 3% en el año 2026'
```

Si `agno_actual` no se entrega se usa el año del sistema.

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
sobre variables (`cnu_afil`, `cnu_cnyg_s_h`, `cnu_sobr_cnyg_s_h`, `cnu_faj`).
Cada argumento puede ser un escalar o un arreglo con un valor por fila. La
tabla `"vigente"` se resuelve fila a fila con el sexo, el `agno_actual` y el
`fsiniestro` de cada observación.

```python
import numpy as np
edades = np.array([55, 65, 75])
cnu.cnu_afiliado_vec(edades, mujer=[0, 1, 0], rp=0.03, agno_actual=2026)
cnu.cnu_afiliado_vec(edades, fsiniestro=[20130101, 20200101, 20240101], rp=0.03)   # rv2009, cb2014, cb2020
cnu.cnu_conyuge_vec(edades, [53, 63, 73], cony_mujer=True, rp=[0.03, np.nan, 0.03])  # fila 1 sin tasa -> nan
cnu.faj_afiliado_vec(edades, rp=0.03)
```

La tasa se resuelve fila a fila con la misma regla que las funciones
escalares (`rv`, `rp`, `agno_vector` o `fsiniestro` anterior a 2014 de cada
observación). Las filas con edad fuera de [20, 110], sin tasa determinable o
con vector de tasas inexistente quedan en `nan` y se emite una advertencia
`cnu.AdvertenciaCNU` con los índices y el motivo.

### Opciones comunes

| Argumento | Descripción |
|---|---|
| `tabla` | Tabla de mortalidad del afiliado: `"vigente"` (por defecto) o un nombre explícito como `"rv2009"`, `"cb2020"`. |
| `tabla_benef` | Tabla del beneficiario: `"vigente"` (por defecto) o un nombre explícito como `"b2006"`, `"b2020"`. |
| `mujer`, `cot_mujer`, `cony_mujer` | Sexo del afiliado o cónyuge; determina la tabla (`cb` para hombres desde 2016). |
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
cnu afil 65 --fsiniestro 20240315 --rp 0.03
cnu afil 65 --mujer --rp 0.03 --pasos
cnu afil 65 --tabla rv2009 --agno-vector 2013 --agno-actual 2013
cnu conyuge 65 63 --rp 0.03 --agno-actual 2026
cnu sobrev 63 --mujer --rp 0.03
cnu faj 65 62 --rp 0.03 --agno-vector 2013
cnu proy 65 --faj --csv --rp 0.03 > trayectoria.csv
cnu tablas
```

```
$ cnu afil 65 --fsiniestro 20240315 --rp 0.03
CNU RP para soltero sin hijos (tabla cb2020h), tasa 3% en el año 2026
15.456439
```

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
* Superintendencia de Pensiones, Nota Técnica N° 9 (noviembre de 2024):
  https://www.spensiones.cl/portal/institucional/594/articles-16151_recurso_1.pdf
* Comisión para el Mercado Financiero, NCG N° 495: publicación de las tablas
  TM2020: https://www.cmfchile.cl/portal/principal/623/w4-propertyvalue-48722.html

## Autores

* George G. Vega Yon, Superintendencia de Pensiones (módulo original en Stata/Mata).
* Francisco Javier Errandonea Terán (conversión a Python).

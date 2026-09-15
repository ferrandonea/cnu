# cnu : Cálculo del Capital Necesario Unitario (CNU) en Python

Paquete Python para el cálculo de Capitales Necesarios Unitarios (CNU),
utilizados en el cálculo de pensiones del sistema chileno. Es la conversión a
Python del módulo de Stata/Mata `cnu` de George G. Vega Yon (Superintendencia
de Pensiones), cuyo código original se conserva en `ado/` y `man/`.

Implementa las fórmulas de CNU del Anexo N° 7 para pensión de vejez o
invalidez y de sobrevivencia del afiliado y de cada beneficiario (cónyuge o
conviviente civil con y sin hijos, hijos no inválidos e inválidos, madre o
padre de hijos no matrimoniales y padres del afiliado), el CNU total de un
grupo familiar con el aporte de cada beneficiario y la cuota mortuoria, la
proyección de pensión en Retiro Programado y el Factor de Ajuste (FAJ,
derogado desde 2022 y conservado solo para cálculos históricos), con todas
las tablas de mortalidad normativas desde 1985 hasta las TM2020 vigentes. La sección
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

# Madre o padre de hijos de filiación no matrimonial: 30% mientras haya hijos con derecho (aquí el menor de 21)
# y 36% después; sin hijos con derecho (h=None), 36% vitalicio; con algún hijo inválido, 30% vitalicio
cnu.cnu_madre_padre(50, 45, 21, rp=0.03, agno_actual=2026)              # 1.370247  (cb2020h, b2020m)
cnu.cnu_madre_padre(50, 45, rp=0.03, agno_actual=2026)                  # 1.370831  (sin hijos con derecho)
cnu.cnu_sobrevivencia_madre_padre(45, 21, hijo_invalido=True, rp=0.03, agno_actual=2026)  # 7.264773  (b2020m)

# Padres del afiliado: 50% cada uno, una llamada por cada padre (madre=True usa la tabla de mujer)
cnu.cnu_padres(65, 88, rp=0.03, agno_actual=2026)                       # 0.161421  (cb2020h, b2020m)
cnu.cnu_padres(65, 88, madre=False, rp=0.03, agno_actual=2026)          # 0.115149  (cb2020h, cb2020h)
cnu.cnu_sobrevivencia_padres(88, rp=0.03, agno_actual=2026)             # 3.089039  (b2020m)

# Grupo familiar completo: el afiliado (o None en sobrevivencia) más la lista de beneficiarios.
# La función decide los tramos (50%/60% del cónyuge, 30%/36% de la madre o el padre no matrimonial)
# a partir de los hijos con derecho de la lista y devuelve el total con el aporte de cada uno
g = cnu.cnu_grupo_familiar(cnu.Afiliado(65), [cnu.Beneficiario("conyuge", 63), cnu.Beneficiario("hijo", 10)],
                           rp=0.03, agno_actual=2026)
g.total                                     # 18.001136  (= 15.456439 + 2.409035 + 0.135662)
[c.cnu for c in g.componentes]              # [15.456439, 2.409035, 0.135662]
[c.etiqueta for c in g.componentes]         # ['afiliado', 'cónyuge con hijos 50%/60%', 'hijo no inválido 15%']
g.componentes[1].porcentajes                # (0.5, 0.6)
g.descripcion   # 'CNU RP para grupo familiar: afiliado, cónyuge con hijos 50%/60%, hijo no inválido 15% (tablas cb2020h b2020m), tasa 3% en el año 2026'
g.to_dict()     # {'total': ..., 'descripcion': ..., 'componentes': [{'tipo': 'afiliado', 'etiqueta': ..., 'porcentajes': [1.0], 'cnu': 15.456439, ...}, ...]}

# Los beneficiarios también se aceptan como tuplas (tipo, edad[, mujer[, parcial]]); un hijo inválido deja
# al cónyuge en 50% vitalicio; sin afiliado se usan las variantes de sobrevivencia
cnu.cnu_grupo_familiar(cnu.Afiliado(65), [("conyuge", 63), ("hijo", 10), ("hijo_invalido", 20)],
                       rp=0.03, agno_actual=2026).componentes[1].etiqueta   # 'cónyuge con hijo inválido 50%'
cnu.cnu_grupo_familiar(None, [("conyuge", 63), ("hijo", 10, True)], rp=0.03, agno_actual=2026).total   # 11.298419

# Cuota mortuoria (cnu.CUOTA_MORTUORIA_UF = 15 UF) como componente separado, en las unidades del saldo:
# valor_uf es el valor de la UF en esas unidades (aquí el saldo está en UF)
cnu.cnu_grupo_familiar(cnu.Afiliado(65), [("conyuge", 63), ("hijo", 10)], valor_uf=1,
                       rp=0.03, agno_actual=2026).total                    # 33.001136  (18.001136 + 15)

# Las exclusiones del artículo 58 lanzan ErrorGrupoFamiliar (un ValueError que cita la regla)
cnu.cnu_grupo_familiar(cnu.Afiliado(65), [("padres", 88), ("conyuge", 63)], rp=0.03, agno_actual=2026)
# ErrorGrupoFamiliar: Los padres del afiliado solo tienen derecho a falta de conyuge, ... (articulo 58 del D.L. N 3.500)

# Factor de ajuste (derogado desde el 1-2-2022: con fecha posterior emite AdvertenciaCNU)
cnu.faj_afiliado(65, rp=0.03, agno_vector=2013, agno_actual=2026)      # 0.037205
cnu.faj_afiliado(65, 62, rp=0.03, agno_vector=2013, agno_actual=2026)  # 0.004659

# Proyección de pensión en retiro programado (con o sin FAJ; con faj=True, misma advertencia).
# Con fecha de cálculo desde el 1-9-2025 (cnu.VIGENCIA_BANDA) aplica la banda del 10% de la Ley N° 21.735
p = cnu.proyectar_pension(65, saldo=1000, rp=0.03, agno_actual=2026)
p.edad, p.saldo, p.pension                       # p.pension[0] = 64.6979 (la primera pensión no cambia)
p.descripcion           # "Trayectoria de pension con banda 10% para afiliado soltero (tabla cb2020) tasa 3% en 2026."
p.edad[p.acotado]       # [90, ..., 97]: períodos donde la banda acotó la pensión; p.pension[25] = 23.8114 (edad 90)
q = cnu.proyectar_pension(65, saldo=1000, rp=0.03, agno_actual=2026, banda=False)   # sin banda: q.pension[25] = 23.7923
cnu.proyectar_pension(65, saldo=1000, rp=0.03, agno_actual=2024)   # antes de la vigencia no hay banda (banda=None)
p = cnu.proyectar_pension(65, saldo=1000, rp=0.03, faj=True, agno_actual=2026)
p.edad, p.saldo, p.pension, p.faj, p.saldo_faj   # p.pension[0] = 63.2245, p.faj = 0.022775
p.to_dataframe()        # requiere pandas

# Compensación por Diferencias de Expectativa de Vida (CEV, Ley N° 21.735): mujer que se pensiona por vejez
# desde el 2-1-2026 (cnu.VIGENCIA_CEV). Factor = CNU del grupo con tabla de mujer / CNU del mismo grupo con
# tabla de hombre de igual edad (tablas vigentes a la fecha de pensión); rv es la tasa implícita promedio de
# rentas vitalicias de vejez de los últimos seis meses; la pensión de referencia (anualidad CEV) va en UF
c = cnu.calcular_cev(65, [("conyuge", 67, False)], pension_referencia=12, fecha_pension=20260301, rv=0.03)
c.cnu_mujer, c.cnu_hombre, c.factor     # 18.498496, 16.948846, 1.091431 (c.diferencia = factor - 1 = 0.091431)
c.porcentaje, c.pension_referencia      # 1.0 (100% a los 65 años), 12 (tope 18 UF)
c.compensacion, c.monto                 # 1.097172 = 12 × (1.091431 − 1) × 1.0; monto mensual 1.10 UF (dos decimales)
c.descripcion   # "CEV para mujer de 65 años pensionada el 20260301, grupo familiar: cónyuge sin hijos
                #  (tablas rv2020m cb2020h / cb2020h), tasa 3%: factor 1.091431, 100% por edad"
c = cnu.calcular_cev(62, [], pension_referencia=30, fecha_pension=20260301, rv=0.03)
c.factor, c.porcentaje, c.pension_referencia, c.monto   # 1.124605, 0.25 (62 años), 18 (acotada), 0.56
c = cnu.calcular_cev(65, [], pension_referencia=1, fecha_pension=20260301, rv=0.03)
c.compensacion, c.monto, c.minimo_aplicado              # 0.138914, 0.25 (mínimo de 0,25 UF), True
cnu.calcular_cev(65, [], pension_referencia=12, fecha_pension=20260301, rv=0.03, mujer=False)   # ErrorCEV: solo mujeres
cnu.calcular_cev(65, [], pension_referencia=12, fecha_pension=20251201, rv=0.03)   # ErrorCEV: anterior a 20260102 (stock)

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
`cnu_sobrevivencia_hijo_invalido_vec`, `cnu_conyuge_con_hijos_vec`,
`cnu_sobrevivencia_conyuge_con_hijos_vec`, `cnu_madre_padre_vec`,
`cnu_sobrevivencia_madre_padre_vec`, `cnu_padres_vec`,
`cnu_sobrevivencia_padres_vec` y `cnu_grupo_familiar_vec` no tienen comando
equivalente. Cada argumento puede ser un escalar o un arreglo con un valor
por fila. La tabla `"vigente"` se resuelve fila a fila con el sexo, el
`agno_actual` y el `fsiniestro` de cada observación.

```python
import numpy as np
edades = np.array([55, 65, 75])
cnu.cnu_afiliado_vec(edades, mujer=[0, 1, 0], rp=0.03, agno_actual=2026)
cnu.cnu_afiliado_vec(edades, fsiniestro=[20130101, 20200101, 20240101], rp=0.03)   # rv2009, cb2014, cb2020
cnu.cnu_conyuge_vec(edades, [53, 63, 73], cony_mujer=True, rp=[0.03, np.nan, 0.03])  # fila 1 sin tasa -> nan
cnu.cnu_hijo_vec(edades, [3, 12, 25], hijo_mujer=[0, 1, 0], rp=0.03)                # fila 2: 0 (24 años o más)
cnu.cnu_hijo_invalido_vec(edades, [3, 12, 25], parcial=[0, 1, 1], rp=0.03)          # tabla mi, sin edad límite
cnu.cnu_conyuge_con_hijos_vec(edades, [53, 63, 73], [3, 12, 25], cony_mujer=True, rp=0.03)  # fila 2: como sin hijos
cnu.cnu_madre_padre_vec(edades, [50, 60, 70], [3, 12, np.nan], rp=0.03)              # fila 2 (nan): sin hijos, 36%
cnu.cnu_padres_vec(edades, [80, 88, 95], madre=[1, 0, 1], rp=0.03)                   # un padre o madre por fila
cnu.faj_afiliado_vec(edades, rp=0.03)

# Grupo familiar por fila: afiliado, cónyuge o conviviente (nan = sin cónyuge) y hasta k hijos (matriz N x k, nan = ausente).
hijos = np.array([[10, 14, np.nan], [np.nan, np.nan, np.nan], [3, np.nan, np.nan]])
cnu.cnu_grupo_familiar_vec(edades, [53, np.nan, 73], hijos, hijos_mujer=[[0, 1, 0]] * 3, rp=0.03, agno_actual=2026)
# array([21.94064 , 15.456439, 13.697482])   cada fila coincide con cnu_grupo_familiar con los mismos beneficiarios
total, comp = cnu.cnu_grupo_familiar_vec(edades, [53, np.nan, 73], hijos, hijos_invalidez=[[0, 0, 0], [0, 0, 0], [2, 0, 0]],
                                         rp=0.03, agno_actual=2026, componentes=True)
comp   # N x (2 + k): afiliado, cónyuge, hijo 1, hijo 2, hijo 3 (nan = ausente); fila 2: hijo inválido parcial (grado 2)
# array([[19.728818,  2.132981,  0.052515,  0.026281,       nan],
#        [15.456439,       nan,       nan,       nan,       nan],
#        [10.706354,  2.124165,  2.20031 ,       nan,       nan]])
```

La tasa se resuelve fila a fila con la misma regla que las funciones
escalares (`rv`, `rp`, `agno_vector` o `fsiniestro` anterior a 2014 de cada
observación). Las filas con edad fuera de [20, 110] (negativa en el caso de
los hijos, que se calculan desde los 0 años), sin tasa determinable o con
vector de tasas inexistente quedan en `nan` y se emite una advertencia
`cnu.AdvertenciaCNU` con los índices y el motivo. En `cnu_grupo_familiar_vec`
también quedan en `nan`, con su motivo, las filas cuyo grupo la norma no
admite o el paquete no cubre (hijos con derecho sin cónyuge, sobrevivencia
sin beneficiarios); `sobrevivencia=True` (escalar o columna) marca las filas
sin afiliado y `valor_uf` agrega la cuota mortuoria como última columna. Los
grupos con madre o padre de hijos no matrimoniales o con padres del afiliado
se calculan con las vectoriales individuales (`cnu_madre_padre_vec`,
`cnu_padres_vec` y sus variantes de sobrevivencia).

### Opciones comunes

| Argumento | Descripción |
|---|---|
| `tabla` | Tabla de mortalidad del afiliado: `"vigente"` (por defecto) o un nombre explícito como `"rv2009"`, `"cb2020"`. |
| `tabla_benef` | Tabla del beneficiario: `"vigente"` (por defecto) o un nombre explícito como `"b2006"`, `"b2020"` (`"mi2020"` para el hijo inválido, cuyo rol es el de inválido). |
| `mujer`, `cot_mujer`, `cony_mujer`, `hijo_mujer` | Sexo del afiliado, cónyuge o hijo; determina la tabla (`cb` para hombres desde 2016). |
| `parcial` | Grado de invalidez del hijo inválido: `False` (por defecto) total, 15% vitalicio; `True` parcial, 15% hasta los 24 años y 11% después. |
| `h` (cónyuge con hijos) | Edad del hijo menor con derecho a pensión: fija el tramo al 50% (hasta que cumpla 24 años) y el tramo al 60% desde entonces. |
| `hijo_invalido` | `True` si algún hijo con derecho a pensión del cónyuge es inválido: 50% vitalicio (la edad `h` no interviene). |
| `u`, `h` (madre o padre no matrimonial) | Edad de la madre o el padre de hijos de filiación no matrimonial y del hijo menor con derecho: 30% hasta que cumpla 24 años y 36% desde entonces; `h=None` (o `nan` en la vectorial) es sin hijos con derecho, 36% vitalicio; `hijo_invalido`, 30% vitalicio. |
| `m` (padres) | Edad del padre o la madre del afiliado; 50% vitalicio cada uno, una llamada (o una fila) por cada padre. |
| `madre` | En las funciones de madre o padre y de padres: `True` (por defecto) si el beneficiario es la madre, `False` si es el padre; fija el sexo de la tabla de beneficiario. |
| `conviviente` | `True` si el beneficiario de las funciones del cónyuge es conviviente civil (Ley N° 20.830): misma fórmula y mismo valor; documenta el rol. |
| `afiliado`, `beneficiarios` (grupo familiar) | `cnu.Afiliado(edad, mujer)` (o una tupla, o `None` en sobrevivencia) y lista de `cnu.Beneficiario(tipo, edad, mujer=None, parcial=False)` con `tipo` en `cnu.TIPOS_BENEFICIARIO` (`conyuge`, `conviviente`, `hijo`, `hijo_invalido`, `madre_padre`, `padres`); `mujer=None` usa el sexo por defecto del tipo (cónyuge mujer, hijo hombre, madre). |
| `valor_uf` (grupo familiar) | Valor de la UF en las unidades del saldo; si se entrega, la cuota mortuoria (15 UF) se agrega como componente separado. |
| `x`, `y`, `hijos` (grupo familiar vectorial) | Edad del afiliado, del cónyuge o conviviente (`nan` = sin cónyuge) y matriz `N x k` con la edad de cada hijo (`nan` = ausente; una columna de largo `N` es un solo hijo). `cot_mujer`, `cony_mujer` (mujer por defecto) fijan el sexo; `hijos_mujer` y `hijos_invalidez` (`cnu.GRADO_NO_INVALIDO` 0, `cnu.GRADO_INVALIDO_TOTAL` 1, `cnu.GRADO_INVALIDO_PARCIAL` 2) tienen la forma de `hijos` o son escalares. `sobrevivencia` marca las filas sin afiliado y `componentes=True` devuelve además la matriz de aportes. |
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
cnu madre-padre 50 45 21 --rp 0.03 --agno-actual 2026 # madre de hijos no matrimoniales con hijos 30%/36%
cnu madre-padre 50 45 --padre --rp 0.03               # padre de hijos no matrimoniales sin hijos con derecho 36%
cnu sobrev-madre-padre 45 21 --hijo-invalido --rp 0.03   # sobrevivencia de madre no matrimonial con hijo inválido 30%
cnu padres 65 88 --rp 0.03 --agno-actual 2026         # madre del afiliado 50% (--padre: el padre, tabla de hombre)
cnu sobrev-padres 88 --rp 0.03                        # sobrevivencia de madre del causante 50%
cnu grupo --afiliado 65 --conyuge 63 --hijo 10 --rp 0.03 --agno-actual 2026   # grupo familiar: aporte de cada uno y total
cnu grupo --afiliado 65 --hijo 10 --hijo 14m --conyuge 62m --hijo-inv 20 total --rp 0.03   # opciones repetibles; sufijo h/m = sexo
cnu grupo --conyuge 63m --hijo 10m --uf 39000 --rp 0.03   # sin --afiliado, sobrevivencia; --uf agrega la cuota mortuoria
cnu faj 65 62 --rp 0.03 --agno-vector 2013
cnu proy 65 --csv --rp 0.03 > trayectoria.csv      # con banda 10% (fecha de cálculo desde el 1-9-2025); columna acotado
cnu proy 65 --sin-banda --rp 0.03                     # sin banda; --banda la fuerza en fechas anteriores
cnu proy 65 --faj --csv --rp 0.03 --agno-actual 2014 > trayectoria.csv   # FAJ histórico
cnu cev 65 --conyuge 67h --pension 12 --fecha-pension 20260301 --rv 0.03   # CEV: mismas opciones de beneficiarios que grupo
cnu cev 62 --pension 30 --fecha-pension 20260301 --rv 0.03                 # 25% a los 62 años; pensión acotada a 18 UF
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
$ cnu madre-padre 50 45 21 --rp 0.03 --agno-actual 2026
CNU RP para madre no matrimonial con hijos 30%/36% (tablas cb2020h b2020m), tasa 3% en el año 2026
 1.370247
$ cnu padres 65 88 --rp 0.03 --agno-actual 2026
CNU RP para madre del afiliado 50% (tablas cb2020h b2020m), tasa 3% en el año 2026
 0.161421
$ cnu grupo --afiliado 65 --conyuge 63 --hijo 10 --rp 0.03 --agno-actual 2026
CNU RP para grupo familiar: afiliado, cónyuge con hijos 50%/60%, hijo no inválido 15% (tablas cb2020h b2020m), tasa 3% en el año 2026
  afiliado                                       15.456439
  cónyuge con hijos 50%/60%                       2.409035
  hijo no inválido 15%                            0.135662
  total                                          18.001136
$ cnu cev 65 --conyuge 67h --pension 12 --fecha-pension 20260301 --rv 0.03
CEV para mujer de 65 años pensionada el 20260301, grupo familiar: cónyuge sin hijos (tablas rv2020m cb2020h / cb2020h), tasa 3%: factor 1.091431, 100% por edad
  CNU mujer (rv2020m cb2020h)                    18.498496
  CNU hombre (cb2020h)                           16.948846
  factor de corrección (mujer/hombre)             1.091431
  porcentaje por edad                                 100%
  pensión de referencia acotada (UF)             12.000000
  compensación calculada (UF)                     1.097172
  monto mensual (UF)                                  1.10
```

En `cnu grupo` cada beneficiario se entrega como `EDAD[h|m]` (el sufijo fija
el sexo; sin él rige el del tipo: cónyuge y conviviente mujer, hijos hombre,
`--madre-padre` y `--padres` madre) y `--hijo-inv` admite además el grado
`total` (por defecto) o `parcial`. Un grupo que la norma no admite (artículo
58) termina con el mensaje en stderr y código de salida 3.

`cnu cev` recibe la edad de la mujer a la fecha de pensión, los beneficiarios
con las mismas opciones repetibles de `cnu grupo` (el cónyuge de una mujer se
indica con `h`), la pensión de referencia mensual en UF (`--pension`), la
fecha de pensión (`--fecha-pension`, que fija las tablas vigentes) y la tasa
de la anualidad (`--rv`, la tasa implícita promedio de rentas vitalicias de
vejez de los seis meses anteriores, que publica la SP). Una CEV que no
corresponde (fecha anterior al 2 de enero de 2026, edad menor que 60,
pensión de referencia nula) termina con código de salida 4.

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
  septiembre de 2026 rige 3,45% desde julio de 2026 (Circular N° 2.417;
  revisado el 15 de septiembre de 2026, ver [Mantención](#mantención)). En
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

### Beneficiarios cubiertos

Están implementados todos los beneficiarios del Anexo N° 7 del Libro III,
en pensión de vejez o invalidez (afiliado vivo, letras 2.x) y en
sobrevivencia (afiliado fallecido, letras 1.x), con los porcentajes del
artículo 58 del D.L. N° 3.500:

| Beneficiario | Vejez o invalidez | Sobrevivencia |
|---|---|---|
| Afiliado | `cnu_afiliado` | |
| Cónyuge sin hijos, 60% | `cnu_conyuge` (letra 2.b) | `cnu_sobrevivencia_conyuge` (letra 1.a) |
| Cónyuge con hijos con derecho a pensión: 50% hasta los 24 años del hijo menor y 60% después, o 50% vitalicio con algún hijo inválido | `cnu_conyuge_con_hijos` (letras 2.c y 2.d) | `cnu_sobrevivencia_conyuge_con_hijos` (letras 1.b y 1.c) |
| Conviviente civil sin hijos o con hijos comunes, misma fórmula con `a` en lugar de `y` | `conviviente=True` en las funciones del cónyuge (letras 2.m, 2.o y 2.q) | ídem (letras 1.l, 1.n y 1.p) |
| Hijo no inválido, 15% hasta los 24 años | `cnu_hijo` (letra 2.e) | `cnu_sobrevivencia_hijo` (letra 1.d) |
| Hijo inválido total (15% vitalicio) o parcial (15% hasta los 24 años y 11% después), con tabla de inválidos | `cnu_hijo_invalido` (letra 2.f) | `cnu_sobrevivencia_hijo_invalido` (letra 1.e) |
| Madre o padre de hijos de filiación no matrimonial: 36% sin hijos con derecho, 30% hasta los 24 años del hijo menor y 36% después, o 30% vitalicio con algún hijo inválido | `cnu_madre_padre` (letras 2.i, 2.j y 2.k) | `cnu_sobrevivencia_madre_padre` (letras 1.h, 1.i y 1.j) |
| Madre o padre del afiliado, 50% cada uno | `cnu_padres` (letra 2.l) | `cnu_sobrevivencia_padres` (letra 1.k) |
| Grupo familiar completo: CNU total como suma del afiliado y de cada beneficiario de la lista, con los tramos del artículo 58 decididos desde los hijos con derecho | `cnu_grupo_familiar`, `cnu grupo` | ídem con afiliado `None` |
| Cuota mortuoria de 15 UF (`CUOTA_MORTUORIA_UF`), componente opcional del grupo familiar en las unidades del saldo (`valor_uf`) | `cnu_grupo_familiar(valor_uf=...)` | ídem |
| Grupo familiar vectorial: afiliado, cónyuge o conviviente y hasta `k` hijos por fila, con total y matriz de componentes; los grupos con madre o padre no matrimonial o con padres del afiliado se calculan con las vectoriales individuales | `cnu_grupo_familiar_vec` | ídem con `sobrevivencia=True` |

Las funciones del hijo reciben su edad desde los 0 años; las del hijo no
inválido devuelven 0 desde los 24 y las del hijo inválido no tienen edad
límite. Las del cónyuge con hijos reciben la edad del hijo menor con derecho
(`h`) y un indicador de hijo inválido; con `h` de 24 o más devuelven
exactamente el valor del cónyuge sin hijos. Las de la madre o el padre de
hijos no matrimoniales siguen la misma mecánica con 30%/36% y admiten
`h=None` (sin hijos con derecho, 36%). Las de los padres del afiliado calculan
a uno de los dos por llamada (50% cada uno); su derecho existe solo a falta de
cónyuge, conviviente civil, hijos y madre o padre no matrimonial, y siempre
que sean carga familiar del afiliado.

`cnu_grupo_familiar` compone todo lo anterior: recibe al afiliado (o `None`
en sobrevivencia) y la lista de beneficiarios, obtiene de ella el hijo menor
con derecho (menor de 24 años) y la presencia de algún hijo inválido para
fijar los tramos 50%/60% del cónyuge o conviviente y 30%/36% de la madre o el
padre no matrimonial (todos los hijos de la lista cuentan para ambos), y
devuelve el total como suma exacta de las funciones individuales. Solo valida
las exclusiones del artículo 58 del D.L. N° 3.500: padres del afiliado junto
con cónyuge, conviviente, hijos o madre o padre no matrimonial, más de un
cónyuge o conviviente, o más de una madre y un padre del afiliado lanzan
`ErrorGrupoFamiliar` (un `ValueError` que cita el artículo), igual que un
grupo con hijos con derecho pero sin cónyuge, conviviente ni madre o padre no
matrimonial (ver [Fuera de alcance](#fuera-de-alcance)).

### Fuera de alcance

El paquete calcula capitales necesarios; lo que sigue queda deliberadamente
fuera y es responsabilidad de quien llama:

* **Elegibilidad de los beneficiarios.** La calidad de estudiante entre los
  18 y los 24 años, la invalidez declarada y su grado, la existencia de la
  unión civil, la filiación de los hijos y la calidad de carga familiar de
  los padres son datos de entrada que el paquete no valida: quien llama
  decide quién integra el grupo y el paquete calcula su capital necesario.
* **Reparto de la pensión de sobrevivencia** entre los beneficiarios
  (mensualidades del Capítulo III de la Letra F del Título I del Libro III):
  es un paso posterior al CNU.
* **Recálculos trimestrales dentro del año.** La proyección de pensión sigue
  siendo anual; la banda del 10% se aplica entre períodos anuales
  consecutivos (ver [Ley N° 21.735](#ley-n-21735)).
* **Stock de la CEV.** La compensación de las pensionadas al 1 de enero de
  2026 (letra a del Capítulo III de la Letra C del Título XIX, con la PAFE y
  las tablas y tasa al 1 de abril de 2025) y la CEV de la pensión de
  invalidez; el paquete cubre el flujo de nuevas pensionadas de vejez.
* **Otros beneficios del Seguro Social Previsional** distintos de la CEV
  (beneficio por años cotizados y demás prestaciones de la Ley N° 21.735).
* **Datos externos.** El paquete no descarga la TITRP, el valor de la UF ni
  la tasa implícita de rentas vitalicias; son entradas (`rp`, `valor_uf`,
  `rv`).
* **Dos combinaciones del Anexo N° 7 sin cónyuge ni madre o padre.** Hijos
  con derecho a pensión sin cónyuge, conviviente ni madre o padre no
  matrimonial (letras 1.f, 1.g, 2.g y 2.h, porcentaje 0,15 + 0,5/n por hijo)
  y conviviente civil sin hijos comunes que concurre con hijos del causante
  (letras 1.m, 1.o, 2.n y 2.p, 15% mientras haya hijos con derecho).
  `cnu_grupo_familiar` rechaza el primer caso con `ErrorGrupoFamiliar`; el
  detalle está en `HANDOFF.md`.

### Ley N° 21.735

La Ley N° 21.735 (marzo de 2025) introdujo una banda de variación máxima del
10% para los recálculos de las pensiones en retiro programado y renta
temporal derivados de los ajustes de la TITRP (desde el 1 de septiembre de
2025) y la Compensación por Diferencias de Expectativa de Vida (CEV),
regulada en la Letra C del Título XIX del Libro III (Norma de Carácter
General N° 350, de 12 de septiembre de 2025). Ninguna de las dos modifica la
fórmula del CNU: la banda actúa sobre la pensión resultante y la CEV es un
beneficio adicional que se calcula con dos CNU. Ambas están implementadas.

**Banda del 10%.** `proyectar_pension` (y `cnu proy`) la aplica cuando la
fecha de cálculo (`fsiniestro` o el 31 de diciembre de `agno_actual`) es
igual o posterior a `cnu.VIGENCIA_BANDA` (20250901); `banda=True` /
`--banda` la fuerza y `banda=False` / `--sin-banda` la desactiva. La
pensión de cada período `j ≥ 1` queda entre el 90% y el 110% de la pensión
del período anterior (la primera pensión no cambia), el saldo se descuenta
con la pensión efectivamente pagada, `p.acotado` (columna `acotado` en la
CLI) marca los períodos donde la banda actuó y la descripción dice "con
banda 10%". La pensión nunca supera el saldo disponible: si la banda exige
más de lo que queda, se paga el saldo y la cuenta se agota. Simplificaciones
documentadas: la norma regula los ajustes trimestrales de la TITRP y esta
proyección es anual, por lo que la banda se aplica entre períodos anuales
consecutivos (base de comparación: la pensión del período anterior), y los
recálculos extraordinarios, que la ley excluye de la banda, no forman parte
de la proyección. Fuente: Ley N° 21.735 y oficio de la Superintendencia de
Pensiones del 17 de abril de 2025 con instrucciones a las AFP (ver
[Referencias](#referencias)).

**CEV.** `calcular_cev` (y `cnu cev`) calcula la compensación mensual de una
mujer que se pensiona por vejez a partir del 2 de enero de 2026
(`cnu.VIGENCIA_CEV`, letra b del Capítulo III de la Letra C del Título XIX)
como `pensión_referencia × (factor − 1) × porcentaje`, con:

* **Factor de corrección**: razón entre el CNU del grupo familiar de la mujer
  (`cnu_grupo_familiar` con `Afiliado(edad, mujer=True)`) y el CNU del mismo
  grupo con la tabla de un hombre de igual edad (`mujer=False`), con las
  tablas vigentes a la fecha de pensión y la edad actuarial. El Compendio
  escribe el factor como esa razón menos 1 (`c.diferencia`); la fórmula es la
  misma. El grupo familiar y el sexo de cada beneficiario se conservan en
  ambos CNU ("para el cálculo del CNU hombre se considerará el saldo y grupo
  familiar que tuviera la mujer a la edad que se pensionó").
* **Tasa de la anualidad** (`rv`): la tasa de interés promedio implícita de
  las rentas vitalicias de vejez otorgadas en los seis meses anteriores a la
  fecha de pensión, que la SP informa mensualmente; el paquete no la
  descarga.
* **Porcentaje por edad de pensión** (`cnu.PORCENTAJE_CEV_POR_EDAD`,
  `porcentaje_cev`), tabla de beneficio del Capítulo II, número 2, letra b:
  65 años o más 100%, 64 años 75%, 63 años 50%, 62 años 25%, 61 años 15%,
  60 años 5%; menos de 60 años 0% (la pensión anticipada del artículo 68 no
  da derecho, y el paquete lanza `ErrorCEV`). No hay recálculos posteriores
  por cumplimiento de años.
* **Tope y mínimo**: la pensión de referencia (la "anualidad CEV", renta
  vitalicia inmediata simple que financia el saldo, en UF) se acota a 18 UF
  (`cnu.TOPE_PENSION_REFERENCIA_UF`) y el beneficio mensual no baja de 0,25
  UF (`cnu.MINIMO_CEV_UF`); el monto se expresa en UF con dos decimales
  (`c.monto`; `c.compensacion` conserva el valor sin redondear ni mínimo).

**Cálculo referencial.** La concesión, la validación de los requisitos y el
pago los hace el Instituto de Previsión Social (IPS) a partir del cálculo de
la AFP (Capítulo IV); este paquete solo reproduce la fórmula. La elegibilidad
(cotización al Fondo Autónomo de Protección Previsional antes de los 50 años,
pensión sin cobertura del SIS, trabajos pesados) es un dato de entrada que no
se valida. Quedan fuera el **stock de pensionadas al 1 de enero de 2026**
(letra a del Capítulo III: se calcula con la PAFE, las tablas y la tasa
vigentes al 1 de abril de 2025 y la edad a esa fecha; una fecha de pensión
anterior a `cnu.VIGENCIA_CEV` lanza `ErrorCEV`) y la pensión de **invalidez**
(letra c: 100% sin escala por edad). Fuentes: Compendio, Libro III, Título
XIX, Letra C, Capítulos II y III, y ficha de ChileAtiende (ver
[Referencias](#referencias)).

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

## Mantención

### TITRP de referencia (cada trimestre)

El paquete no fija tasa por defecto ni accede a la red: la TITRP es un dato
de entrada (`rp`). La documentación cita la cifra vigente solo como
referencia, y hay que contrastarla cada trimestre, cuando la SP publica la
circular del nuevo período (enero, abril, julio y octubre).

| | |
|---|---|
| Dónde la publica la SP | [Tasas de interés para el cálculo de los retiros programados y las rentas temporales](https://www.spensiones.cl/apps/tasas/tasdescto.php) |
| Circular vigente | N° 2.417, 3,45% desde julio de 2026 |
| Última revisión | 15 de septiembre de 2026 (sin cambios) |

Lugares que citan la cifra y que hay que actualizar si cambia:

1. README, [Lo que debe entregar el usuario](#lo-que-debe-entregar-el-usuario):
   la cifra, la circular, la fecha de revisión y el ejemplo
   `cnu.cnu_afiliado(65, rp=0.0345, agno_actual=2026)   # 14.755007`.
2. README, [Uso desde Python](#uso-desde-python): el ejemplo de edad
   actuarial `cnu.cnu_afiliado(65.7, rp=0.0345, agno_actual=2026)   # 14.322867`.
3. README, [Línea de comandos](#línea-de-comandos): la primera línea de
   ejemplo (`tasa 3.45%`) y `cnu afil 65.7 --rp 0.0345 --agno-actual 2026`.
4. Esta tabla (circular vigente y fecha de revisión).
5. `tests/test_readme.py::test_estado_normativo_y_edad_actuarial` y
   `tests/test_tasa.py::test_tasa_explicita`, que reproducen los valores
   14.755007 y 14.322867 con `rp=0.0345`. Los demás tests que usan 0,0345
   (`test_proyeccion.py`, `test_edad_actuarial.py`, `test_faj_derogado.py`)
   la usan como tasa cualquiera y no dependen de la circular.
6. `CHANGELOG.md`: una línea con la cifra, la circular y la fecha de
   revisión, aunque no haya cambiado.

Para obtener los valores nuevos basta ejecutar los ejemplos con la tasa
nueva (`uv run cnu afil 65 --rp <tasa> --agno-actual <año>`) y copiar el
resultado. El comando que verifica que README y tests coinciden es:

```
uv run pytest tests/test_readme.py tests/test_tasa.py
```

`tests/test_readme.py::test_defaults_publicos_sin_2013_ni_0_03` y
`test_ningun_ejemplo_depende_de_una_tasa_por_defecto` garantizan además que
la actualización no introduzca una tasa por defecto.

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
  Compensación por Diferencias de Expectativa de Vida (Ley N° 21.735; NCG
  N° 350): https://www.spensiones.cl/portal/compendio/596/w3-propertyvalue-10821.html;
  Capítulo II, Requisitos y tabla de porcentaje por edad:
  https://www.spensiones.cl/portal/compendio/596/w3-propertyvalue-10834.html;
  Capítulo III, Cálculo de la compensación (factor de corrección, anualidad
  CEV, tope de 18 UF y mínimo de 0,25 UF):
  https://www.spensiones.cl/portal/compendio/596/w3-propertyvalue-10835.html
* ChileAtiende, Compensación por Diferencias de Expectativa de Vida para las
  mujeres (porcentajes por edad, concesión por el IPS):
  https://www.chileatiende.gob.cl/fichas/130452-compensacion-por-diferencia-de-expectativa-de-vida-para-las-mujeres
* Superintendencia de Pensiones, Ley N° 21.735 (26 de marzo de 2025):
  https://www.spensiones.cl/portal/institucional/594/w3-article-16483.html
  y banda de variación máxima para el retiro programado:
  https://www.spensiones.cl/portal/institucional/594/w3-article-16568.html
* Comisión para el Mercado Financiero, NCG N° 495: publicación de las tablas
  TM2020: https://www.cmfchile.cl/portal/principal/623/w4-propertyvalue-48722.html

## Autores

* George G. Vega Yon, Superintendencia de Pensiones (módulo original en Stata/Mata).
* Francisco Javier Errandonea Terán (conversión a Python).

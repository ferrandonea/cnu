# cnu : Cálculo del Capital Necesario Unitario (CNU) en Python

Paquete Python para el cálculo de Capitales Necesarios Unitarios (CNU),
utilizados en el cálculo de pensiones del sistema chileno. Es la conversión a
Python del módulo de Stata/Mata `cnu` de George G. Vega Yon (Superintendencia
de Pensiones), cuyo código original se conserva en `ado/` y `man/`.

Implementa las fórmulas de CNU para pensión de vejez de afiliado y de cónyuge
sin hijos, para pensión de sobrevivencia de cónyuge sin hijos, la proyección
de pensión en Retiro Programado y el Factor de Ajuste (FAJ).

## Instalación

Requiere Python 3.12 o superior. Con [uv](https://docs.astral.sh/uv/):

```
uv sync            # crea el entorno e instala numpy
uv run pytest      # corre los tests
```

O con pip: `pip install .`

## Uso desde Python

```python
import cnu

# CNU de afiliado soltero de 65 años, vector de tasas 2013, año de cálculo 2013
cnu.cnu_afiliado(65, agno_vector=2013, agno_actual=2013)        # 13.016877

# Con tasa única de retiro programado, o renta vitalicia
cnu.cnu_afiliado(65, rp=0.0366, agno_actual=2014)               # 13.377535
cnu.cnu_afiliado(67, rv=0.032, agno_actual=2013)

# CNU del cónyuge (se suma al del afiliado para obtener el CNU total)
cnu.cnu_conyuge(65, 63, cony_mujer=True, agno_vector=2011, agno_actual=2011)  # 2.231859

# CNU de sobrevivencia para cónyuge sin hijos
cnu.cnu_sobrevivencia_conyuge(65, mujer=False, agno_actual=2013)

# Factor de ajuste
cnu.faj_afiliado(65, rp=0.03, agno_actual=2014)                 # 0.066178
cnu.faj_afiliado(65, 62, rp=0.03, agno_actual=2014)             # 0.013094

# Proyección de pensión en retiro programado (con o sin FAJ)
p = cnu.proyectar_pension(65, saldo=1000, rp=0.03, faj=True)
p.edad, p.saldo, p.pension, p.faj, p.saldo_faj
p.to_dataframe()        # requiere pandas
```

### Versiones vectoriales

Las funciones con sufijo `_vec` equivalen a los comandos de Stata que operan
sobre variables (`cnu_afil`, `cnu_cnyg_s_h`, `cnu_sobr_cnyg_s_h`, `cnu_faj`).
Cada argumento puede ser un escalar o un arreglo con un valor por fila.

```python
import numpy as np
edades = np.array([55, 65, 75])
cnu.cnu_afiliado_vec(edades, mujer=[0, 1, 0], agno_actual=2013)
cnu.cnu_conyuge_vec(edades, [53, 63, 73], cony_mujer=True, rp=[0.03, np.nan, 0.03])
cnu.faj_afiliado_vec(edades, rp=0.03)
```

Las filas con edad fuera de [20, 110] o con vector de tasas inexistente quedan
en `nan` y se emite una advertencia `cnu.AdvertenciaCNU` con los índices.

### Opciones comunes

| Argumento | Descripción |
|---|---|
| `tabla` | Tabla de mortalidad del afiliado (`"rv2009"` por defecto). |
| `tabla_benef` | Tabla del beneficiario (`"b2006"` por defecto). |
| `mujer`, `cot_mujer`, `cony_mujer` | Sexo del afiliado o cónyuge. |
| `agno_vector` | Año del vector de tasas para Retiro Programado (2013 por defecto). |
| `agno_actual` | Año de cálculo; ajusta las tablas por mejoramiento (por defecto, el año actual). |
| `rv` | Tasa de renta vitalicia. Si se entrega, el CNU es de RV. |
| `rp` | Tasa única de retiro programado. Si no se entrega, se usa el vector. |
| `fsiniestro` | Fecha del siniestro `YYYYMMDD`; asigna la tabla vigente a esa fecha. |
| `pasos` | Imprime el cálculo periodo a periodo. |
| `dir_tablas`, `dir_vectores` | Directorios con tablas o vectores propios. |

## Línea de comandos

```
cnu afil 65 --agno-actual 2013
cnu afil 65 --rp 0.0366 --pasos
cnu conyuge 65 63 --agno-actual 2011 --agno-vector 2011
cnu sobrev 65 --mujer
cnu faj 65 62 --rp 0.03
cnu proy 65 --faj --csv > trayectoria.csv
cnu tablas
```

## Tablas de mortalidad y vectores de tasas

Las tablas incluidas viven en `src/cnu/data` como CSV:

* `cnu_tabmor_[tipo][año][género].csv` con columnas `edad, qx, aa`
  (tipo `rv` afiliado, `b` beneficiario, `mi` invalidez; género `h`/`m`).
  Disponibles: rv1985, rv2004, rv2009, b1985, b2006, mi2006.
* `cnu_vec[año].csv` con columnas `t, tasa` (191 periodos).
  Disponibles: 2009 a 2013.

Para usar tablas propias, guárdelas en un directorio con esos nombres (en CSV
o en el formato binario original de Mata) y pase `dir_tablas` / `dir_vectores`.
Las funciones `guardar_tabla_mortalidad`, `guardar_vector_tasas`,
`leer_matriz_mata` y `escribir_matriz_mata` permiten crear y convertir archivos.

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

Compendio de Normas de la Superintendencia de Pensiones, Libro III, Anexo N 7
(Capitales necesarios).

## Autores

* George G. Vega Yon, Superintendencia de Pensiones (módulo original en Stata/Mata).
* Francisco Javier Errandonea Terán (conversión a Python).

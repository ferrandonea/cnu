# Handoff: actualización de tablas de mortalidad

Fecha de revisión: 11 de septiembre de 2026.

## Diagnóstico

El paquete conserva por defecto las tablas `RV-2009` para el afiliado y
`B-2006` para beneficiarios (`src/cnu/core.py`). La asignación automática de
`src/cnu/tablas.py` también termina en 2009/2006.

Sin embargo, el repositorio ya contiene los CSV oficiales de 2014 y 2020:

- `CB-2014-H`, `RV-2014-M`, `B-2014-M` y `MI-2014-H/M`.
- `CB-2020-H`, `RV-2020-M`, `B-2020-M` y `MI-2020-H/M`.

Las tablas 2020 no funcionan todavía. Sus CSV tienen 18 columnas:
`edad`, `qx` y los factores `aa2021` a `aa2036`. El cargador actual exige
exactamente tres columnas (`edad`, `qx`, `aa`) y, por lo tanto, las rechaza.

La normativa vigente desde el 1 de julio de 2023 usa:

| Persona | Hombre | Mujer |
|---|---|---|
| Afiliado no inválido | `CB2020h` | `RV2020m` |
| Beneficiario no inválido | `CB2020h` | `B2020m` |
| Inválido | `MI2020h` | `MI2020m` |

Las TM2020 tienen factores de mejoramiento bidimensionales. Para una edad
`x` y año de cálculo `a`:

```text
qx(x,a) = qx(x,2020) * producto[t=2021..a] (1 - AA(x,t))
```

Desde 2036 se debe repetir el factor `AA(x,2036)` para cada año posterior.
Al proyectar desde una edad inicial, cada edad futura debe evaluarse en su
año calendario correspondiente: `año_actual + edad_futura - edad_inicial`.

## Vigencias que debe implementar la selección automática

| Fecha de pensión | Afiliado H | Afiliada M | Benef. H | Benef. M | Inválido H/M |
|---|---|---|---|---|---|
| hasta 31-01-2005 | RV1985 | RV1985 | B1985 | B1985 | MI1985 |
| 01-02-2005 a 31-01-2008 | RV2004 | RV2004 | B1985 | B1985 | MI1985 |
| 01-02-2008 a 30-06-2010 | RV2004 | RV2004 | B2006 | B2006 | MI2006 |
| 01-07-2010 a 30-06-2016 | RV2009 | RV2009 | B2006 | B2006 | MI2006 |
| 01-07-2016 a 30-06-2023 | CB2014 | RV2014 | CB2014 | B2014 | MI2014 |
| desde 01-07-2023 | CB2020 | RV2020 | CB2020 | B2020 | MI2020 |

## Implementación sugerida

1. Adaptar la lectura de tablas en `src/cnu/tablas.py` para conservar la
   cabecera CSV. Los binarios Mata históricos pueden seguir tratándose como
   matrices de tres columnas.
2. Ampliar `TablaMortalidad` para representar:
   - tablas históricas: `aa` unidimensional;
   - TM2020: `aa` bidimensional y `agnos_aa=[2021, ..., 2036]`.
3. Hacer que `desde_matriz`, `como_matriz`, la carga y el guardado admitan
   ambos esquemas. Para una matriz cruda de más de tres columnas, exigir los
   años de los factores explícitamente, porque no se pueden inferir sin la
   cabecera.
4. Separar las dos fórmulas dentro de `qx_mejorado`:
   - histórica: conservar la fórmula actual;
   - TM2020: producto acumulado por edad y año, repitiendo el factor 2036
     después de ese año.
5. Agregar un selector que devuelva **tipo y año**, no solo el año. Esto es
   necesario porque para hombres la tabla cambia de `RV`/`B` a `CB` en 2016.
   Debe recibir fecha, rol (`rv`, `b` o `mi`) y género.
6. Mantener `agno_tabla_por_siniestro` por compatibilidad, pero implementar
   internamente una función más completa, por ejemplo
   `tabla_por_fecha(fecha, tipo, genero) -> (tipo, año)`.
7. Cambiar los defaults fijos por un valor simbólico como `"vigente"` y
   resolverlo usando sexo, rol y año/fecha de cálculo. Una tabla explícita
   como `"rv2009"` debe seguir respetándose.
8. Pasar género y rol al resolver tablas desde `cnu_afiliado`, `cnu_conyuge`
   y `cnu_sobrevivencia_conyuge`; actualizar también CLI, funciones
   vectoriales, FAJ, proyecciones y `describir`.
9. Actualizar el README: tablas disponibles, nueva forma bidimensional,
   vigencias y ejemplos actuales. Conservar ejemplos históricos indicando
   explícitamente su año.

Una decisión de API importante: solo `agno_actual` no distingue enero de
julio de 2023 (ni de 2016). Se recomienda usar `fsiniestro`/fecha de pensión
cuando esté disponible y documentar qué convención se usa cuando solo se
entrega un año (por ejemplo, fin de año).

## Pruebas mínimas

- Cargar las cinco TM2020 y verificar forma, edades y años de factores.
- Reproducir el ejemplo oficial:
  `CB-H-2020`, edad 65, año 2022 = `0.00852603117` aproximadamente.
- Verificar una edad futura: desde 65 en 2022, el `qx` de edad 70 debe usar
  los factores de esa fila desde 2021 hasta 2027.
- Verificar que 2037 repita una vez más el factor de 2036.
- Probar todas las fronteras de vigencia: 31-01/01-02-2005,
  31-01/01-02-2008, 30-06/01-07-2010, 30-06/01-07-2016 y
  30-06/01-07-2023.
- Verificar que `"vigente"` en 2026 seleccione `CB2020h`/`RV2020m` para
  afiliados y `CB2020h`/`B2020m` para beneficiarios.
- Mantener los valores de referencia históricos cuando se usa 2011-2014 o
  una tabla explícita.
- Ejecutar:

```bash
UV_CACHE_DIR=/tmp/cnu-uv-cache uv run pytest -q
```

Estado antes de implementar: **59 pruebas pasan**.

## Otro desfase detectado

El default de tasas todavía es el vector 2013 (`AGNO_VECTOR = 2013`). La nota
técnica de la SP indica que desde enero de 2014 el vector fue reemplazado por
una tasa única, y la TITRP vigente se ajusta periódicamente. Conviene tratar
esto en un cambio separado: no fijar silenciosamente una tasa que caduca,
permitir entregarla explícitamente y documentar que los vectores 2009-2013
son históricos.

## Fuentes oficiales

- SP, Nota Técnica N° 9 (noviembre de 2024):
  https://www.spensiones.cl/portal/institucional/594/articles-16151_recurso_1.pdf
- SP, Título X, tablas de mortalidad:
  https://www.spensiones.cl/portal/compendio/596/w3-propertyvalue-3483.html
- SP, Anexo N° 9, TM2020 y fórmula bidimensional:
  https://www.spensiones.cl/portal/compendio/596/fo-article-15659.pdf
- CMF, publicación de las TM2020 (NCG N° 495):
  https://www.cmfchile.cl/portal/principal/623/w4-propertyvalue-48722.html
- CMF, planilla histórica usada para contrastar los CSV:
  https://www.cmfchile.cl/portal/principal/623/articles-99359_recurso_1.xlsx

## Archivos temporales de la revisión

En `tmp/pdfs/` quedaron el Anexo N° 9, las páginas 14-15 renderizadas y la
planilla histórica de la CMF. Son artefactos de verificación no versionados;
se pueden eliminar cuando termine la actualización.

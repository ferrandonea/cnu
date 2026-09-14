# Handoff: pendientes fuera de alcance

Fecha de revisión: 14 de septiembre de 2026 (cierre del PRD #8, versión 0.3.0).

## Estado del paquete

El paquete está alineado con la norma vigente en lo que cubre: fórmulas del
Anexo N° 7 para afiliado, cónyuge sin hijos y sobrevivencia de cónyuge sin
hijos; tablas de mortalidad y vigencias del Título X (1985 a TM2020, con
mejoramiento bidimensional 2021-2036); tasa explícita (TITRP) sin vector por
defecto; edad actuarial; FAJ conservado solo para cálculos históricos. La
sección "Estado normativo" del README documenta el detalle.

Los puntos siguientes quedaron explícitamente fuera del PRD #8 y son
candidatos a PRDs nuevos, en orden de valor.

## 1. Beneficiarios pendientes (el más valioso)

Hoy solo se calcula el CNU de tres casos. Para obtener el CNU total de un
grupo familiar completo faltan, según el Anexo N° 7 del Libro III:

| Beneficiario | Situación |
|---|---|
| Hijos con derecho a pensión (menores de 18, estudiantes hasta 24) | No implementado |
| Hijos inválidos (pensión vitalicia) | No implementado |
| Cónyuge con hijos con derecho a pensión | No implementado |
| Conviviente civil (con y sin hijos) | No implementado |
| Madre o padre de hijos de filiación no matrimonial | No implementado |
| Padres del afiliado | No implementado |
| Cuota mortuoria | No implementado |

Consideraciones para la implementación:

- Las fórmulas de hijos usan una edad límite (18 o 24 años) y una
  probabilidad de supervivencia hasta esa edad, no la vitalicia. Los hijos
  inválidos se tratan con tabla `mi` y sin edad límite.
- El cónyuge con hijos tiene un porcentaje de pensión distinto (50% en vez de
  60%) mientras haya hijos con derecho, por lo que el CNU del cónyuge depende
  del CNU de los hijos. La forma más limpia es una función de grupo familiar
  que reciba la lista de beneficiarios y devuelva el CNU total y sus
  componentes.
- El conviviente civil se asimila al cónyuge desde la Ley N° 20.830 (octubre
  de 2015); conviene reutilizar `cnu_conyuge` y `cnu_sobrevivencia_conyuge`
  con un parámetro de rol o un alias.
- Los padres del afiliado solo tienen derecho a falta de otros beneficiarios
  y con condiciones (carga familiar), así que la validación de elegibilidad
  debe quedar fuera del cálculo o bien documentada.
- Todo caso nuevo necesita: función escalar en `src/cnu/core.py`, versión
  vectorial en `src/cnu/vectorial.py`, subcomando en `src/cnu/cli.py`,
  `describir`, ejemplos en README y valores de referencia. Como no hay rutinas
  Mata originales para estos casos, los valores de referencia deben
  construirse a mano con la fórmula del Anexo y documentarse en
  `tests/test_referencias.py`.

## 2. Ley N° 21.735: banda del 10% y CEV

Ninguna de las dos modifica la fórmula del CNU; actúan sobre la pensión
resultante, por lo que corresponden a un módulo aparte (por ejemplo, junto a
`src/cnu/proyeccion.py`):

- **Banda de variación máxima del 10%** en los recálculos trimestrales del
  retiro programado, vigente desde el 1 de septiembre de 2025. Afecta a
  `proyectar_pension`: la pensión de cada período no puede variar más de 10%
  respecto de la anterior. Requiere definir la regla exacta de la banda
  (base de comparación, tratamiento del primer recálculo) a partir de la
  circular de la SP.
- **Compensación por Diferencias de Expectativa de Vida (CEV)**, Letra C del
  Título XIX del Libro III: beneficio adicional para mujeres, financiado por
  el Seguro Social Previsional. Es un cálculo independiente del CNU que usa
  las diferencias de expectativa de vida entre las tablas de hombres y
  mujeres.

## 3. Actualización trimestral de la TITRP

El README fija como referencia 3,45% desde julio de 2026 (Circular N° 2.417).
Cada trimestre hay que revisar esa cifra en la sección "Estado normativo" y
en los ejemplos que la usan. El paquete no la descarga ni la fija por
defecto a propósito: es un dato de entrada (`rp`).

Fuente: https://www.spensiones.cl/apps/tasas/tasdescto.php

## Fuentes oficiales

- SP, Compendio, Libro III, Anexo N° 7 (capitales necesarios) y Título X
  (tablas de mortalidad):
  https://www.spensiones.cl/portal/compendio/596/w3-propertyvalue-3483.html
- SP, Compendio, Libro III, Título I, Letra F, Capítulo III (retiro
  programado, recálculo y edad actuarial):
  https://www.spensiones.cl/portal/compendio/596/w3-propertyvalue-3223.html
- SP, Compendio, Libro III, Título XIX, Letra C (CEV):
  https://www.spensiones.cl/portal/compendio/596/w3-propertyvalue-10821.html
- SP, Ley N° 21.735 y banda de variación máxima:
  https://www.spensiones.cl/portal/institucional/594/w3-article-16483.html
  https://www.spensiones.cl/portal/institucional/594/w3-article-16568.html
- SP, Nota Técnica N° 8 (TITRP):
  https://www.spensiones.cl/portal/institucional/594/w3-article-15569.html

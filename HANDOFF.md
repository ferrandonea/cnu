# Handoff: pendientes fuera de alcance

Fecha de revisión: 15 de septiembre de 2026 (cierre del PRD #17, versión
0.4.0, más auditoría de las fórmulas contra el Anexo N° 7 del mismo día).

El paquete cubre todos los beneficiarios del Anexo N° 7 del Libro III, el
CNU total de un grupo familiar con cuota mortuoria, la banda de variación
máxima del 10% y la CEV de la Ley N° 21.735, y documenta la mantención
trimestral de la TITRP. La sección "Estado normativo" del README detalla lo
cubierto y lo que queda fuera; aquí solo se anotan los pendientes que
podrían dar origen a un PRD nuevo.

## Resultado de la auditoría contra el Anexo N° 7 (15-09-2026)

Se contrastó cada función escalar con las fórmulas del PDF oficial del
Anexo N° 7 y el factor de mejoramiento con el PDF del Anexo N° 9 (enlaces
en «Fuentes oficiales»):

- Coinciden término a término: afiliado (2.a), cónyuge sin hijos (2.b y
  1.a), hijos no inválidos (2.e y 1.d), hijo inválido total y parcial (2.f y
  1.e, incluido el coeficiente 0,04 × 11/24 de la parcial), cónyuge con hijos
  (2.c, 2.d, 1.b, 1.c), madre o padre no matrimonial (2.i a 2.k, 1.h a 1.j),
  padres del causante (2.l, 1.k) y conviviente civil (2.m, 2.o, 2.q, 1.l,
  1.n, 1.p).
- El mejoramiento bidimensional reproduce el ejemplo oficial del Anexo N° 9
  (`q65,2022` de CB-H-2020 = 0,008526031) y la regla de mantener constante el
  factor de 2036.
- Las vigencias de tablas y la TITRP del README (3,45% desde julio de 2026,
  Circular N° 2.417) coinciden con el Compendio y con la página de tasas de
  la SP a la fecha de revisión.

## 1. Cuota mortuoria: discrepancia con la norma (prioridad alta)

| Anexo | Norma | Estado |
|---|---|---|
| Punto 3 | `CNCM = 15 · A_x`, con `A_x = (1/l_x) Σ_{t=0}^{w} (l_{x+t} − l_{x+t+1}) / (1+i_{t+1})^{t+1}` (valor actual esperado de 15 UF pagaderas al fallecimiento del afiliado) | `cnu_grupo_familiar(valor_uf=...)` suma 15 UF planas (`CUOTA_MORTUORIA_UF * valor_uf`) |

Es la única fórmula implementada que se aparta del Anexo. Orden de
magnitud: para un hombre de 65 años, tabla `cb2020` (CB-H-2020), 3% y año
2026,
`A_65 ≈ 0,536` y `CNCM ≈ 8,05 UF`, no 15 UF.

Consideraciones:

- `A_x` usa la tabla del afiliado (o del causante) y la misma tasa del CNU;
  se calcula con la misma `qx_mejorado` que las anualidades y cabe en
  `core.py` como función pública (p.ej. `cnu_cuota_mortuoria(x, mujer, ...)`)
  que devuelva `15 · A_x` en UF; `cnu_grupo_familiar` la multiplicaría por
  `valor_uf`.
- En sobrevivencia (afiliado ya fallecido) la cuota mortuoria no se
  proyecta: se descuenta del saldo como 15 UF. Hay que decidir el
  comportamiento con `afiliado=None`.
- Requiere actualizar el README (sección "Beneficiarios cubiertos" y el
  ejemplo de `valor_uf`), `test_grupo.py` y `cnu_grupo_familiar_vec`.

## 2. Combinaciones del Anexo N° 7 no implementadas

| Letras del Anexo | Caso | Estado |
|---|---|---|
| 1.f, 1.g, 2.g, 2.h | Hijos con derecho a pensión (no inválidos e inválidos) sin cónyuge, conviviente civil ni madre o padre de filiación no matrimonial: porcentaje 0,15 + 0,5/n por hijo, con `n` hijos con derecho | No implementado; `cnu_grupo_familiar` lanza `ErrorGrupoFamiliar` |
| 1.m, 1.o, 2.n, 2.p | Conviviente civil sin hijos comunes que concurre con hijos del causante: 15% mientras haya hijos con derecho (más 45% diferido en 1.m y 2.n) | No implementado |
| Letras 1.d y 1.f, párrafo final | Grupo familiar compuesto por un solo hijo con edad actuarial de 23 o más años: el CNU total es la pensión por el número de meses que le restan para cumplir 24 | No implementado; el paquete calcula la anualidad temporal normal |
| Punto 1, párrafo introductorio (NCG N° 260 de 2020) | Dos o más cónyuges: el 60% (o el porcentaje que corresponda) se divide por el número de cónyuges, con dos decimales, y acrece al desaparecer uno | No implementado; `cnu_grupo_familiar` rechaza más de un cónyuge o conviviente |

Consideraciones:

- El porcentaje 0,5/n depende del número de hijos con derecho y cambia
  cuando cada hijo cumple 24 años, así que el CNU de cada hijo pasa a tener
  tantos tramos como hijos menores haya; conviene resolverlo dentro de
  `cnu_grupo_familiar`, que ya conoce la lista completa, y no en las
  funciones escalares por hijo.
- El conviviente sin hijos comunes con hijos del causante sigue la mecánica
  de dos tramos del cónyuge con hijos (temporal hasta los 24 del hijo menor)
  pero con 15% en el primer tramo y 0% después, salvo hijos inválidos
  (15% vitalicio). Puede modelarse con la misma función de tramos
  cambiando los porcentajes.
- La regla del hijo único de 23 años necesita la edad en meses (no solo la
  edad actuarial entera), por lo que requiere fecha de nacimiento o meses
  restantes como entrada.
- Todos los casos necesitan valor de referencia transcrito a mano del Anexo
  en `tests/test_referencias.py`, versión vectorial, subcomando y ejemplo en
  el README, como el resto.

## 3. Sin fuente primaria confirmada

- **Definición de edad actuarial.** El paquete redondea la edad exacta al
  entero más cercano con el medio hacia arriba (seis meses o más suben). El
  Compendio usa el término "edad actuarial" (Capítulo III de la Letra F del
  Título I del Libro III y Anexo N° 7) pero en las páginas revisadas
  (Retiro Programado, Definiciones) no aparece la regla de redondeo. Queda
  pendiente ubicar la cita exacta o la circular que la fija y anotarla en
  el README; si la regla oficial fuera distinta (p.ej. años cumplidos sin
  redondeo) cambia `edad_entera` y todos los valores de referencia.
- **Fin de tabla `w`.** Las anualidades suman hasta la edad 110 como el
  Mata original. Con todas las tablas incluidas `q_110 = 1`, así que el
  resultado no cambia; con tablas propias que superen los 110 años sí.

## 4. Fuera de alcance por diseño

Quedaron fuera de la spec #17 y no está previsto incorporarlos:

- Validar la elegibilidad de los beneficiarios (estudios, carga familiar,
  unión civil, invalidez declarada): son datos de entrada.
- Reparto de la pensión de sobrevivencia entre beneficiarios (Capítulo III
  de la Letra F del Título I): posterior al CNU.
- Recálculos trimestrales dentro del año en la proyección (sigue anual).
- Descargar la TITRP, el valor de la UF o la tasa implícita de rentas
  vitalicias.
- CEV del stock de pensionadas al 1 de enero de 2026 y CEV de la pensión de
  invalidez.
- Beneficio por años cotizados y demás prestaciones del Seguro Social
  Previsional distintas de la CEV.
- Cambios en las rutinas Mata o en el paquete de Stata incluido en `ado/`.

## Fuentes oficiales

- SP, Compendio, Libro III, Anexo N° 7 (capitales necesarios y cuota
  mortuoria; la página muestra las fórmulas como imágenes, el PDF las trae
  completas):
  https://www.spensiones.cl/portal/compendio/596/w3-propertyvalue-3262.html
  https://www.spensiones.cl/portal/compendio/596/fo-article-7253.pdf
- SP, Compendio, Libro III, Título X, Capítulo IX (tablas TM2020, vigencia
  desde el 1 de julio de 2023) y Anexo N° 9 (factores de mejoramiento
  bidimensionales y ejemplo numérico):
  https://www.spensiones.cl/portal/compendio/596/w3-propertyvalue-10624.html
  https://www.spensiones.cl/portal/compendio/596/fo-article-15659.pdf
- SP, Compendio, Libro III, Título I, Letra F, Capítulo III (retiro
  programado, recálculo y edad actuarial):
  https://www.spensiones.cl/portal/compendio/596/w3-propertyvalue-3223.html
- SP, Compendio, Libro III, Título XIX, Letra C (CEV):
  https://www.spensiones.cl/portal/compendio/596/w3-propertyvalue-10821.html
- SP, tasas de interés para retiros programados y rentas temporales (TITRP):
  https://www.spensiones.cl/apps/tasas/tasdescto.php

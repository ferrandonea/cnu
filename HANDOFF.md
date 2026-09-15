# Handoff: pendientes fuera de alcance

Fecha de revisión: 15 de septiembre de 2026 (cierre del PRD #17, versión
0.4.0).

El paquete cubre todos los beneficiarios del Anexo N° 7 del Libro III, el
CNU total de un grupo familiar con cuota mortuoria, la banda de variación
máxima del 10% y la CEV de la Ley N° 21.735, y documenta la mantención
trimestral de la TITRP. La sección "Estado normativo" del README detalla lo
cubierto y lo que queda fuera; aquí solo se anotan los pendientes que
podrían dar origen a un PRD nuevo.

## 1. Dos combinaciones del Anexo N° 7 sin cónyuge ni madre o padre

| Letras del Anexo | Caso | Estado |
|---|---|---|
| 1.f, 1.g, 2.g, 2.h | Hijos con derecho a pensión (no inválidos e inválidos) sin cónyuge, conviviente civil ni madre o padre de filiación no matrimonial: porcentaje 0,15 + 0,5/n por hijo, con `n` hijos con derecho | No implementado; `cnu_grupo_familiar` lanza `ErrorGrupoFamiliar` |
| 1.m, 1.o, 2.n, 2.p | Conviviente civil sin hijos comunes que concurre con hijos del causante: 15% mientras haya hijos con derecho | No implementado |

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
- Ambos casos necesitan valor de referencia transcrito a mano del Anexo en
  `tests/test_referencias.py`, versión vectorial, subcomando y ejemplo en el
  README, como el resto.

## 2. Fuera de alcance por diseño

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

- SP, Compendio, Libro III, Anexo N° 7 (capitales necesarios):
  https://www.spensiones.cl/portal/compendio/596/w3-propertyvalue-3262.html
- SP, Compendio, Libro III, Título I, Letra F, Capítulo III (retiro
  programado, recálculo y edad actuarial):
  https://www.spensiones.cl/portal/compendio/596/w3-propertyvalue-3223.html
- SP, Compendio, Libro III, Título XIX, Letra C (CEV):
  https://www.spensiones.cl/portal/compendio/596/w3-propertyvalue-10821.html

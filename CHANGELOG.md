# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.

El formato se basa en [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
y el proyecto sigue [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Compensación por Diferencias de Expectativa de Vida (CEV, Ley N° 21.735;
  Compendio, Libro III, Título XIX, Letra C): `calcular_cev` y `cnu cev`
  para una mujer que se pensiona por vejez desde el 2 de enero de 2026
  (`VIGENCIA_CEV`). Factor de corrección como razón entre el CNU del grupo
  familiar con tabla de mujer y con tabla de hombre de igual edad
  (`cnu_grupo_familiar`, tablas vigentes a la fecha de pensión, tasa `rv`),
  porcentaje por edad de pensión (`PORCENTAJE_CEV_POR_EDAD`,
  `porcentaje_cev`: 100% a los 65 años, 75/50/25/15/5% de 64 a 60), pensión
  de referencia acotada a 18 UF (`TOPE_PENSION_REFERENCIA_UF`) y monto
  mínimo de 0,25 UF (`MINIMO_CEV_UF`); resultado `ResultadoCEV` con ambos
  grupos, y `ErrorCEV` para hombre, fecha anterior a la vigencia, edad menor
  que 60 o pensión nula. Cálculo referencial (la concesión la hace el IPS);
  el stock al 1 de enero de 2026 y la pensión de invalidez quedan fuera.
  README: ejemplos verificados y sección "Estado normativo" con la CEV
  implementada.
- README: sección "Mantención" con la lista de verificación trimestral de la
  TITRP de referencia (dónde la publica la SP, circular vigente, lugares del
  README y tests que citan la cifra y comando que los verifica).

### TITRP de referencia

- Revisada el 15 de septiembre de 2026 contra la página de la SP: sigue
  vigente 3,45% desde julio de 2026 (Circular N° 2.417); README, ejemplos y
  tests sin cambios.

## [0.3.0] — 2026-09-14

Alinea los defaults del paquete con la norma vigente (PRD #8).

### Added

- Regla única de tasa (`tasas_por_periodo`, `agno_vector_efectivo`,
  `INICIO_TITRP`): `rv`, `rp` (TITRP) o `agno_vector` explícitos; sin ellos,
  solo un `fsiniestro` anterior al 1 de enero de 2014 usa el vector del año
  del siniestro. `describir` y la primera línea de la CLI muestran la tasa
  efectiva (`tasa 3.45%` o `vector 2013`).
- Las funciones vectoriales y `faj_afiliado_vec` resuelven la tasa fila a
  fila; las filas sin tasa determinable quedan en `nan` y se acumulan en una
  `AdvertenciaCNU` que distingue "sin tasa" de "vector inexistente".
- `edad_actuarial(fecha_nacimiento, fecha_calculo)`: edad actuarial a partir
  de dos fechas (`YYYYMMDD` o `datetime.date`), con el medio hacia arriba.
- `DEROGACION_FAJ` (20220201) y `faj_derogado`; advertencia `AdvertenciaCNU`
  en el FAJ y en `proyectar_pension(faj=True)` para fechas de cálculo desde
  el 1 de febrero de 2022.
- CLI: sin tasa determinable termina con el mensaje de la API en stderr y
  código de salida 2, sin traza; las advertencias van a stderr sin cambiar el
  código; las edades posicionales admiten decimales y se indica la edad
  actuarial usada.
- README: sección "Estado normativo" (alcance, TITRP, edad actuarial, FAJ
  derogado, beneficiarios pendientes, Ley N° 21.735) y referencias al
  Compendio y a la página de tasas de la SP.

### Changed

- **Incompatible:** desaparece el vector de tasas por defecto
  (`AGNO_VECTOR` pasa de 2013 a `None`). Sin `rv`, `rp` ni `agno_vector`, y
  sin siniestro anterior a 2014, las funciones escalares, las proyecciones y
  el FAJ lanzan `ValueError`; los cálculos históricos deben indicar
  `agno_vector` explícito.
- **Incompatible:** `faj_afiliado` y `proyectar_pension` pierden el default
  `rp=0.03`, y la CLI (`cnu faj`, `cnu proy`) el default `--rp 0.03`.
- **Incompatible:** las edades se redondean a edad actuarial (entero más
  cercano, medio hacia arriba) en vez de truncarse; `65.7` ahora se calcula
  como 66. La validación del rango 20-110 ocurre tras el redondeo.
- `faj_afiliado` usa el vector para la trayectoria del CNU solo cuando
  `agno_vector` es explícito; en caso contrario, la misma tasa constante `rp`
  de la capitalización (como `faj_afiliado_vec`).
- Las filas vectoriales con `rv` faltante ya no quedan en `nan` en silencio:
  siguen la regla general de tasa.

### Deprecated

- Factor de Ajuste (`faj_afiliado`, `faj_afiliado_vec`, `calcular_faj`,
  `proyectar_pension(faj=True)`, `cnu faj`, `cnu proy --faj`): derogado por la
  Ley N° 21.419 desde el 1 de febrero de 2022. Se conserva solo para
  reproducir cálculos históricos y advierte con fechas posteriores.

## [0.2.0] — 2026-09-14

### Added

- Carga, guardado y listado de las tablas TM2020 (`cb2020h`, `rv2020m`,
  `b2020m`, `mi2020h/m`) con factores de mejoramiento bidimensionales
  (`edad, qx, aa2021, ..., aa2036`); `TablaMortalidad.bidimensional` y
  `agnos_aa`.
- Fórmula de mejoramiento bidimensional (Anexo N° 9 de la SP): producto
  acumulado de factores por edad y año calendario, repitiendo el factor 2036
  en adelante.
- Tipo de tabla `cb` (combinada, hombres afiliados y beneficiarios desde 2014)
  y selección automática de las TM2014.
- Selector público `tabla_por_fecha(fecha, rol, genero)` con las seis
  ventanas de vigencia (1985, 2004, 2006/2009, 2014, 2020); constantes
  `ROL_AFILIADO`, `ROL_BENEFICIARIO`, `ROL_INVALIDO` y punto único de
  resolución `tabla_mortalidad`.
- Nombre simbólico `"vigente"` (`TABLA_VIGENTE`) que resuelve la tabla según
  rol, sexo y fecha: fecha del siniestro o, en su defecto, el 31 de diciembre
  de `agno_actual` (convención de fin de año).
- `describir` y la salida con `pasos` muestran la tabla efectivamente
  resuelta (tipo, año y sexo); `cnu tablas` indica el esquema de factores de
  cada tabla.
- Error claro al pedir una combinación tipo/año/sexo inexistente (`cb2009`,
  `rv2020` para hombres), con referencia a `tablas_disponibles`.
- README: tablas incluidas, vigencias, default `"vigente"`, fórmulas de
  mejoramiento, tablas propias en ambos esquemas, ejemplos con TM2020 y
  fuentes oficiales; tests que reproducen los ejemplos del README.

### Changed

- Las tablas por defecto (`tabla`, `tabla_benef`) pasan de `rv2009`/`b2006` a
  `"vigente"` en las funciones de CNU, FAJ, proyecciones, versiones
  vectoriales y CLI. Los cálculos sin tabla explícita usan ahora las TM2020;
  los valores históricos se reproducen indicando el año de cálculo
  (2011-2014) o la tabla explícita.
- `agno_tabla_por_siniestro` cubre todas las vigencias hasta 2020.
- Las proyecciones (`proyectar_cnu`, `proyectar_pension`) y el FAJ resuelven
  las tablas una sola vez al inicio de la trayectoria.
- El CNU de cónyuge extiende `qx` con 1 más allá de la edad máxima de la
  tabla (las TM2014/TM2020 terminan en 110).

PRD #1

## [0.1.0]

### Added

- Conversión a Python del módulo de Stata/Mata `cnu`: CNU de afiliado,
  cónyuge y sobrevivencia, versiones vectoriales, proyección de pensión en
  Retiro Programado, Factor de Ajuste y línea de comandos `cnu`.

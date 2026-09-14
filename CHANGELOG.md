# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.

El formato se basa en [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
y el proyecto sigue [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

# TASKS — PRD #1

**PRD:** #1 Actualizar tablas de mortalidad: TM2014, TM2020 (factores de mejoramiento bidimensionales) y selección automática de la tabla vigente por fecha, rol y sexo, con default `"vigente"`.

Repo: `ferrandonea/cnu` (fork; `upstream` = `gvegayon/cnu`). Tests: `UV_CACHE_DIR=/tmp/cnu-uv-cache uv run pytest -q` (59 pasan al inicio).

## Tareas (orden por dependencia)

- [x] #2 Prefactor: punto único de resolución de tabla de mortalidad en el núcleo — completado
- [ ] #3 Cargar, guardar y listar las TM2020 (factores de mejoramiento bidimensionales) — pendiente (sin bloqueos)
- [ ] #4 Mejoramiento bidimensional TM2020 y CNU con tabla 2020 explícita — pendiente (bloqueado por #3)
- [ ] #5 Selección de tabla por fecha de siniestro con todas las vigencias (1985–2020) — pendiente (bloqueado por #2, #4)
- [ ] #6 Default `"vigente"` con convención de fin de año en CNU, FAJ, proyecciones, vectoriales y CLI — pendiente (bloqueado por #5)
- [ ] #7 README y docstrings: tablas 2014/2020, vigencias y default vigente — pendiente (bloqueado por #6)

Frontera inicial: #2 y #3 (independientes entre sí).

Este archivo es efímero: se elimina con `/close-prd 1`.

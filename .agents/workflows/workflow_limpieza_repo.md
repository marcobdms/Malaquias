# Workflow: Limpieza del Repositorio

## Objetivo
Limpiar el repositorio de archivos innecesarios sin tocar código de la aplicación.

## Tareas en orden

### 1. Actualizar .gitignore raíz
Añade estas líneas al .gitignore en la raíz del proyecto si no están:
```
node_modules/
.agent/
*.log
frontend/node_modules/
```

### 2. Eliminar node_modules del tracking
```bash
git rm -r --cached node_modules
git rm -r --cached frontend/node_modules
```
Si alguno no existe, ignora el error y continúa.

### 3. Eliminar .agent del tracking
```bash
git rm -r --cached .agent
```

### 4. Cambiar licencia a propietaria
Reemplaza el contenido del archivo LICENSE en la raíz con:
```
Copyright (c) 2025 Marco Perero Borges. All rights reserved.

This software and its source code are proprietary and confidential.
Unauthorized copying, distribution, modification, or use of this software,
via any medium, is strictly prohibited without the express written
permission of the author.
```

### 5. Commit final
```bash
git add .
git commit -m "chore: remove node_modules and agent files, update license and gitignore"
```

## IMPORTANTE
- No modificar ningún archivo .py, .jsx, .css, .json de configuración
- Solo limpieza de archivos basura y metadata
- El push lo hace el usuario manualmente

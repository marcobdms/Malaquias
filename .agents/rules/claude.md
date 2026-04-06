---
trigger: always_on
---

# Reglas obligatorias para TODOS los agentes — NUNCA violar

## 🔴 GIT — PROHIBIDO ABSOLUTAMENTE

- **NUNCA hacer `git push`** — solo el usuario Marco hace push manualmente
- **NUNCA hacer `git merge`** — puede generar conflictos irresolubles
- **NUNCA hacer `git stash` ni `git stash pop`** — genera conflictos ocultos
- **NUNCA hacer `git rebase`** — reescribo historial, peligroso
- **NUNCA hacer `git rm -r --cached` en directorios grandes** — bloquea el repo
- **Sí puedes**: `git add`, `git commit`, `git status`, `git log`, `git diff`, `git checkout <file>` (para restaurar un archivo)

## 🔴 EJECUCIÓN PARALELA — PROHIBIDA

- Los agentes NO deben ejecutarse simultáneamente sobre el mismo repositorio
- Si detectas que otro proceso git sigue corriendo (`git status` falla o hay `.git/index.lock`), DETENTE y avisa al usuario antes de continuar
- Un agente a la vez. Espera a que el anterior termine.

## 🟡 ANTES DE MODIFICAR CÓDIGO

- Lee siempre `CLAUDE.md` en la raíz del proyecto
- Lee el archivo que vas a modificar COMPLETO antes de tocarlo
- Si el archivo tiene marcadores `<<<<<<< / ======= / >>>>>>>`, **NO lo modifiques**. Avisa al usuario: "Este archivo tiene conflictos de merge sin resolver, necesito que los resuelvas primero."
- No borres funcionalidad existente. Si algo funcionaba, lo mantienes.

## 🟡 ALCANCE DE TRABAJO

- Trabaja SOLO en los archivos necesarios para tu tarea
- No toques archivos fuera del alcance de tu workflow
- Cada workflow tiene su lista de archivos — respétala

## ✅ LECTURA INICIAL OBLIGATORIA

Lee siempre CLAUDE.md en la raíz del proyecto antes de hacer cualquier cambio
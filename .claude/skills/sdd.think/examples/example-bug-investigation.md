# Example: Bug Investigation

**User prompt:** `/sdd.think por qué el sync no actualiza las keys nuevas del config?`

---

**Investigation output:**

## Qué está pasando

Cuando un usuario con `.sdd.json` de una versión anterior ejecuta `sdd sync`, las keys nuevas
(como `baseBranch`) no se agregan. Solo se actualiza el campo `version`.

## Por qué sucede

En `src/commands/sync.ts:70-71`, después de copiar los skills, el sync solo hace:

```typescript
config.version = packageVersion;
writeProjectConfig(projectRoot, config);
```

El objeto `config` es exactamente lo que se leyó del `.sdd.json` del usuario. Si ese archivo no
tenía `baseBranch`, el objeto tampoco lo tiene. Se escribe de vuelta sin las keys nuevas.

## Archivos involucrados

- `src/commands/sync.ts` — `syncSkills()` líneas 69-71, donde se escribe el config
- `src/utils/config.ts` — `createDefaultConfig()` tiene el schema completo con defaults
- `src/utils/merge.ts` — `deepMerge()` ya existe y hace exactamente lo que se necesita, pero no se usa en producción

## Sugerencia

Usar `deepMerge(createDefaultConfig(...), config)` antes de escribir. Esto:
1. Genera el config default completo (con todas las keys)
2. Lo mezcla con el config del usuario (overlay wins)
3. Keys nuevas se agregan con defaults, keys existentes se preservan

El fix es de ~5 líneas en `syncSkills()`.

---

*Quieres que lo implemente? Puedes ejecutar `/sdd.develop` con esta descripción.*

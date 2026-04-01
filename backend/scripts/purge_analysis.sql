-- Borrado completo de todos los análisis (ofertas + candidatos)
-- Los usuarios se mantienen intactos

-- Primero borramos candidatos (dependen de ofertas via FK)
DELETE FROM candidatos;

-- Luego borramos ofertas
DELETE FROM ofertas;

-- Verificación
SELECT 'Candidatos restantes:', COUNT(*) FROM candidatos;
SELECT 'Ofertas restantes:', COUNT(*) FROM ofertas;
SELECT 'Usuarios (intactos):', COUNT(*) FROM users;

# Guía de Sincronización Google Sheets con PostgreSQL

## 📋 Resumen de Cambios

Se ha actualizado el sistema de sincronización con Google Sheets para soportar PostgreSQL además de SQLite. Los cambios principales son:

1. **Actualización de imports**: Ahora usa el sistema de base de datos v2 con abstracción
2. **Soporte multi-base de datos**: Detecta automáticamente si usas SQLite o PostgreSQL
3. **Monitoreo inteligente**: 
   - SQLite: Monitoreo de archivos + polling
   - PostgreSQL: Solo polling (más frecuente)

## 🚀 Cómo Funciona

### Detección Automática

El sistema detecta automáticamente qué base de datos estás usando:

```python
from src.database import db_settings

# El sistema lee automáticamente:
db_settings.db_type  # "sqlite" o "postgresql"
```

### Estrategias de Monitoreo

- **SQLite**: 
  - Monitorea cambios en el archivo `DB/executions.db`
  - Verifica checksums cada 10 segundos
  
- **PostgreSQL**:
  - No monitorea archivos
  - Verifica checksums cada 5 segundos (más frecuente)

## 🔧 Configuración

### 1. Verificar Configuración de PostgreSQL

Asegúrate de que las variables de entorno estén configuradas:

```bash
# Verificar variables
echo $AUTOTRAINX_DB_TYPE
echo $AUTOTRAINX_DB_HOST
echo $AUTOTRAINX_DB_NAME

# Si no están configuradas:
source ~/.bashrc
```

### 2. Verificar Configuración de Google Sheets

El archivo `config.yaml` debe tener:

```yaml
google_sheets_sync:
  enabled: true
  spreadsheet_id: "tu-id-de-spreadsheet"
  sync_interval: 300
```

### 3. Verificar Credenciales

Necesitas el archivo `credentials.json` en la raíz del proyecto.

## 📝 Uso

### Probar la Sincronización

```bash
# Ejecutar pruebas completas
python test_sheets_sync_postgresql.py
```

Esto verificará:
- ✅ Conexión a la base de datos (PostgreSQL o SQLite)
- ✅ Configuración de Google Sheets
- ✅ Sincronización manual
- ✅ Servicio de monitoreo

### Ejecutar el Daemon

```bash
# Ejecutar en primer plano (para ver logs)
python sheets_sync_daemon.py

# Ejecutar como daemon (background)
python sheets_sync_daemon.py --daemon

# Ver estado
python sheets_sync_daemon.py --status

# Detener daemon
python sheets_sync_daemon.py --stop
```

### Logs

Los logs se guardan en:
```
logs/sheets_sync_daemon.log
```

## 🔍 Verificación

### 1. Verificar que está usando PostgreSQL

En los logs deberías ver:
```
Starting database watcher with postgresql backend
PostgreSQL connection: localhost:5432/autotrainx
Database type: postgresql
Started monitoring postgresql database via periodic polling
```

### 2. Verificar Sincronización

Cuando hay cambios en la base de datos:
```
Database content change detected via checksum (postgresql)
Triggering Google Sheets synchronization from postgresql database...
Sync completed: Full sync completed successfully
Synced 150 records
```

## 🐛 Solución de Problemas

### Error: "Google Sheets sync is disabled"

Verifica `config.yaml`:
```yaml
google_sheets_sync:
  enabled: true  # Debe ser true
```

### Error: "credentials.json file not found"

1. Descarga las credenciales de Google Cloud Console
2. Guárdalas como `credentials.json` en la raíz del proyecto

### Error: "Failed to connect to database"

Para PostgreSQL:
```bash
# Verificar servicio
sudo systemctl status postgresql

# Verificar conexión
psql -h localhost -U autotrainx -d autotrainx
```

### El daemon no detecta cambios

1. Verifica que esté usando PostgreSQL:
   ```bash
   grep "Database type" logs/sheets_sync_daemon.log
   ```

2. Espera al menos 5 segundos (intervalo de polling)

3. Verifica manualmente:
   ```bash
   python test_sheets_sync_postgresql.py
   ```

## 📊 Diferencias entre SQLite y PostgreSQL

| Característica | SQLite | PostgreSQL |
|----------------|--------|------------|
| Detección de cambios | Archivo + Checksum | Solo Checksum |
| Intervalo de verificación | 10 segundos | 5 segundos |
| Concurrencia | Limitada | Excelente |
| Performance con múltiples usuarios | Regular | Excelente |

## 🚀 Mejoras Futuras

1. **PostgreSQL LISTEN/NOTIFY**: Notificaciones en tiempo real
2. **Connection pooling**: Ya implementado en DatabaseManager
3. **Bulk operations**: Para sincronizar grandes volúmenes

## 📝 Resumen

El sistema ahora:
- ✅ Detecta automáticamente SQLite o PostgreSQL
- ✅ Usa la estrategia de monitoreo adecuada
- ✅ Mantiene compatibilidad con ambas bases de datos
- ✅ No requiere cambios en la configuración de Google Sheets

Para usar con PostgreSQL, simplemente:
1. Configura las variables de entorno de PostgreSQL
2. Ejecuta el daemon normalmente
3. ¡Listo! La sincronización funcionará automáticamente
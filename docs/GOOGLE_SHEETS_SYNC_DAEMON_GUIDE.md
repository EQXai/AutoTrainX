# Guía del Daemon de Sincronización con Google Sheets

## 📋 Tabla de Contenidos

1. [Introducción](#introducción)
2. [Requisitos Previos](#requisitos-previos)
3. [Configuración Inicial](#configuración-inicial)
4. [Uso del Daemon](#uso-del-daemon)
5. [Gestión con Scripts](#gestión-con-scripts)
6. [Monitoreo y Logs](#monitoreo-y-logs)
7. [Solución de Problemas](#solución-de-problemas)
8. [Configuración Avanzada](#configuración-avanzada)
9. [Referencia de Comandos](#referencia-de-comandos)

---

## 🚀 Introducción

El daemon de sincronización mantiene Google Sheets actualizado automáticamente con los datos de tu base de datos AutoTrainX. Funciona tanto con SQLite como con PostgreSQL.

### Características principales:
- ✅ Sincronización automática en tiempo real
- ✅ Soporte para SQLite y PostgreSQL
- ✅ Monitoreo inteligente de cambios
- ✅ Reintentos automáticos en caso de error
- ✅ Logs detallados para debugging

---

## 📋 Requisitos Previos

### 1. Google Sheets API

Necesitas credenciales de Google Cloud:

```bash
# El archivo debe existir en la raíz del proyecto
ls credentials.json
# o en la ubicación configurada
ls settings/google_credentials.json
```

### 2. Configuración de AutoTrainX

El archivo `config.yaml` debe tener habilitada la sincronización:

```yaml
google_sheets_sync:
  enabled: true
  spreadsheet_id: "tu-id-de-spreadsheet"
  credentials_path: "credentials.json"  # o tu ruta personalizada
```

### 3. Base de Datos Configurada

Para PostgreSQL, las variables de entorno deben estar configuradas:

```bash
# Verificar configuración
echo $AUTOTRAINX_DB_TYPE
echo $AUTOTRAINX_DB_HOST
echo $AUTOTRAINX_DB_NAME
```

---

## ⚙️ Configuración Inicial

### Paso 1: Verificar la Instalación

```bash
# Ejecutar pruebas de conexión
python test_sheets_sync_postgresql.py
```

Deberías ver:
- ✅ Successfully connected to postgresql/sqlite
- ✅ Google Sheets sync is enabled
- ✅ Sync completed successfully

### Paso 2: Primera Sincronización Manual

```bash
# Sincronizar manualmente para verificar
python -c "from src.sheets_sync.integration import manual_full_sync; import asyncio; asyncio.run(manual_full_sync('.'))"
```

---

## 🎮 Uso del Daemon

### Método 1: Script de Gestión (Recomendado)

```bash
# Ver ayuda
./manage_sheets_sync.sh help

# Iniciar daemon
./manage_sheets_sync.sh start -d

# Ver estado
./manage_sheets_sync.sh status

# Detener
./manage_sheets_sync.sh stop
```

### Método 2: Comando Directo

```bash
# Iniciar en primer plano (ver logs)
python sheets_sync_daemon.py

# Iniciar como daemon (background)
python sheets_sync_daemon.py --daemon

# Ver estado
python sheets_sync_daemon.py --status

# Detener
python sheets_sync_daemon.py --stop
```

### Método 3: Con PostgreSQL Específicamente

```bash
# Usar el script específico de PostgreSQL
./start_sheets_sync_postgresql.sh --daemon
```

---

## 📜 Gestión con Scripts

### Script Principal: `manage_sheets_sync.sh`

```bash
# Comandos disponibles:
./manage_sheets_sync.sh start      # Iniciar en primer plano
./manage_sheets_sync.sh start -d   # Iniciar en background
./manage_sheets_sync.sh stop       # Detener daemon
./manage_sheets_sync.sh restart    # Reiniciar daemon
./manage_sheets_sync.sh status     # Ver estado actual
./manage_sheets_sync.sh logs       # Ver últimos 50 logs
./manage_sheets_sync.sh follow     # Seguir logs en tiempo real
./manage_sheets_sync.sh test       # Ejecutar pruebas
```

### Ejemplos de Uso

```bash
# Workflow típico
./manage_sheets_sync.sh status    # Verificar si está corriendo
./manage_sheets_sync.sh start -d   # Iniciar si no está corriendo
./manage_sheets_sync.sh follow     # Ver logs en tiempo real
```

---

## 📊 Monitoreo y Logs

### Ubicación de Logs

```bash
# Log principal del daemon
logs/sheets_sync_daemon.log

# Ver logs recientes
tail -50 logs/sheets_sync_daemon.log

# Seguir logs en tiempo real
tail -f logs/sheets_sync_daemon.log
```

### Qué Buscar en los Logs

#### Inicio Exitoso:
```
Database watcher service started successfully
Started monitoring postgresql database via periodic polling
Google Sheets sync is enabled
```

#### Sincronización Exitosa:
```
Database content change detected via checksum (postgresql)
Triggering Google Sheets synchronization from postgresql database...
Sync completed: Full sync completed successfully
Synced 150 records
```

#### Errores Comunes:
```
ERROR - Failed to connect to database
ERROR - Google Sheets API error
WARNING - Rate limit exceeded, retrying
```

---

## 🐛 Solución de Problemas

### El daemon no detecta cambios

1. **Verificar que está usando la base de datos correcta:**
   ```bash
   grep "Database type:" logs/sheets_sync_daemon.log | tail -5
   ```

2. **Para PostgreSQL, verificar variables de entorno:**
   ```bash
   # Detener daemon
   ./manage_sheets_sync.sh stop
   
   # Reiniciar con variables correctas
   ./manage_sheets_sync.sh restart
   ```

3. **Verificar intervalo de polling:**
   - SQLite: cada 10 segundos
   - PostgreSQL: cada 5 segundos

### Error de autenticación con Google

1. **Verificar credenciales:**
   ```bash
   ls -la credentials.json
   # o
   ls -la settings/google_credentials.json
   ```

2. **Verificar permisos del archivo:**
   ```bash
   chmod 600 credentials.json
   ```

3. **Regenerar token si es necesario:**
   ```bash
   rm token.json  # Si existe
   python test_sheets_sync_postgresql.py  # Regenerará el token
   ```

### El daemon se detiene inesperadamente

1. **Verificar logs de error:**
   ```bash
   grep ERROR logs/sheets_sync_daemon.log | tail -20
   ```

2. **Verificar memoria:**
   ```bash
   ps aux | grep sheets_sync_daemon
   ```

3. **Reiniciar con más logging:**
   ```bash
   # Editar sheets_sync_daemon.py y cambiar nivel de log a DEBUG
   ./manage_sheets_sync.sh restart
   ```

---

## 🔧 Configuración Avanzada

### Cambiar Intervalo de Sincronización

Editar `src/sheets_sync/db_watcher.py`:

```python
# Línea ~169
check_interval = 10 if self.db_type == "sqlite" else 5  # segundos
```

### Configurar Rate Limiting

En `config.yaml`:

```yaml
google_sheets_sync:
  sync_settings:
    rate_limiting:
      requests_per_minute: 60
      burst_limit: 10
```

### Filtrar Qué Sincronizar

Modificar `src/sheets_sync/integration.py` para agregar filtros:

```python
# Ejemplo: solo sincronizar ejecuciones recientes
executions = db_manager.list_executions(
    status=ExecutionStatus.COMPLETED,
    limit=1000
)
```

---

## 📚 Referencia de Comandos

### Comandos del Daemon

| Comando | Descripción |
|---------|-------------|
| `python sheets_sync_daemon.py` | Iniciar en primer plano |
| `python sheets_sync_daemon.py --daemon` | Iniciar en background |
| `python sheets_sync_daemon.py --stop` | Detener daemon |
| `python sheets_sync_daemon.py --status` | Ver estado y PID |

### Scripts de Gestión

| Script | Descripción |
|--------|-------------|
| `./manage_sheets_sync.sh` | Script principal de gestión |
| `./start_sheets_sync_postgresql.sh` | Iniciar con PostgreSQL |
| `./test_sheets_sync_postgresql.py` | Ejecutar pruebas |

### Ubicaciones Importantes

| Archivo/Directorio | Descripción |
|-------------------|-------------|
| `logs/sheets_sync_daemon.log` | Log principal |
| `.sheets_sync_daemon.pid` | Archivo PID del daemon |
| `config.yaml` | Configuración principal |
| `credentials.json` | Credenciales de Google |

---

## 🎯 Tips y Mejores Prácticas

1. **Monitoreo Regular:**
   ```bash
   # Agregar a crontab para verificar cada hora
   0 * * * * /home/user/AutoTrainX/manage_sheets_sync.sh status
   ```

2. **Rotación de Logs:**
   ```bash
   # Rotar logs semanalmente
   mv logs/sheets_sync_daemon.log logs/sheets_sync_daemon.log.$(date +%Y%m%d)
   ./manage_sheets_sync.sh restart
   ```

3. **Backup de Configuración:**
   ```bash
   # Guardar configuración
   cp config.yaml config.yaml.backup
   cp credentials.json credentials.json.backup
   ```

4. **Verificación Post-Deploy:**
   ```bash
   # Después de actualizar código
   ./manage_sheets_sync.sh test
   ./manage_sheets_sync.sh restart
   ./manage_sheets_sync.sh status
   ```

---

## 🚨 Seguridad

1. **Proteger Credenciales:**
   ```bash
   chmod 600 credentials.json
   chmod 600 token.json
   ```

2. **No Compartir Logs:**
   - Los logs pueden contener IDs sensibles
   - Limpiar antes de compartir

3. **Limitar Acceso al Spreadsheet:**
   - Solo dar permisos necesarios
   - Revisar permisos regularmente

---

## 📞 Soporte

Si encuentras problemas:

1. Revisa los logs detallados
2. Ejecuta las pruebas: `./manage_sheets_sync.sh test`
3. Verifica la configuración de Google Sheets
4. Asegúrate de que la base de datos esté accesible

El daemon está diseñado para ser robusto y recuperarse automáticamente de la mayoría de errores temporales.
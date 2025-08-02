# Guía Completa de PostgreSQL para AutoTrainX

## 📋 Tabla de Contenidos

1. [Introducción](#introducción)
2. [Instalación de PostgreSQL](#instalación-de-postgresql)
3. [Configuración Inicial](#configuración-inicial)
4. [Migración de SQLite a PostgreSQL](#migración-de-sqlite-a-postgresql)
5. [Configuración de AutoTrainX](#configuración-de-autotrainx)
6. [Visualización de Datos](#visualización-de-datos)
7. [Mantenimiento](#mantenimiento)
8. [Solución de Problemas](#solución-de-problemas)
9. [Scripts de Utilidad](#scripts-de-utilidad)

---

## 🚀 Introducción

AutoTrainX soporta tanto SQLite como PostgreSQL. PostgreSQL ofrece:
- ✅ Mejor rendimiento con múltiples usuarios
- ✅ Sin errores de "database is locked"
- ✅ Consultas más eficientes
- ✅ Soporte para JSON nativo (JSONB)
- ✅ Mejor escalabilidad

### Requisitos
- Ubuntu 20.04+ o similar
- Python 3.8+
- Permisos sudo para instalación

---

## 📦 Instalación de PostgreSQL

### Opción 1: Instalación Manual

```bash
# Actualizar repositorios
sudo apt update

# Instalar PostgreSQL
sudo apt install postgresql postgresql-contrib

# Verificar instalación
sudo systemctl status postgresql
```

### Opción 2: Script Automático

Usa el script `database_utils/setup_postgresql.sh` (ver sección Scripts de Utilidad).

```bash
chmod +x database_utils/setup_postgresql.sh
./database_utils/setup_postgresql.sh
```

---

## ⚙️ Configuración Inicial

### 1. Crear Usuario y Base de Datos

```bash
# Acceder como usuario postgres
sudo -u postgres psql

# Dentro de PostgreSQL:
CREATE USER autotrainx WITH PASSWORD '1234';
CREATE DATABASE autotrainx OWNER autotrainx;
GRANT ALL PRIVILEGES ON DATABASE autotrainx TO autotrainx;
\q
```

### 2. Verificar Conexión

```bash
psql -h localhost -U autotrainx -d autotrainx
# Contraseña: 1234
```

---

## 🔄 Migración de SQLite a PostgreSQL

### 1. Verificar Datos Existentes

```bash
# Ver tamaño de base de datos SQLite
ls -lh DB/executions.db

# Contar registros
sqlite3 DB/executions.db "SELECT COUNT(*) FROM executions;"
```

### 2. Ejecutar Migración

```bash
# Migración simple (recomendado)
python database_utils/migrate_simple.py

# O migración completa
python src/database/migrate_to_postgresql.py \
  --source DB/executions.db \
  --target postgresql://autotrainx:1234@localhost/autotrainx
```

### 3. Verificar Migración

```bash
python database_utils/verify_postgresql.py
```

---

## 🔧 Configuración de AutoTrainX

### Opción 1: Variables de Entorno (Temporal)

```bash
export AUTOTRAINX_DB_TYPE=postgresql
export AUTOTRAINX_DB_HOST=localhost
export AUTOTRAINX_DB_PORT=5432
export AUTOTRAINX_DB_NAME=autotrainx
export AUTOTRAINX_DB_USER=autotrainx
export AUTOTRAINX_DB_PASSWORD=1234
```

### Opción 2: Configuración Permanente

```bash
# Agregar al archivo .bashrc
echo '# AutoTrainX PostgreSQL Configuration' >> ~/.bashrc
echo 'export AUTOTRAINX_DB_TYPE=postgresql' >> ~/.bashrc
echo 'export AUTOTRAINX_DB_HOST=localhost' >> ~/.bashrc
echo 'export AUTOTRAINX_DB_PORT=5432' >> ~/.bashrc
echo 'export AUTOTRAINX_DB_NAME=autotrainx' >> ~/.bashrc
echo 'export AUTOTRAINX_DB_USER=autotrainx' >> ~/.bashrc
echo 'export AUTOTRAINX_DB_PASSWORD=1234' >> ~/.bashrc

# Recargar configuración
source ~/.bashrc
```

### Opción 3: Modificar main.py

Editar `/home/eqx/AutoTrainX/main.py` y agregar después de los imports:

```python
import os

# Force PostgreSQL configuration
os.environ['AUTOTRAINX_DB_TYPE'] = 'postgresql'
os.environ['AUTOTRAINX_DB_HOST'] = 'localhost'
os.environ['AUTOTRAINX_DB_PORT'] = '5432'
os.environ['AUTOTRAINX_DB_NAME'] = 'autotrainx'
os.environ['AUTOTRAINX_DB_USER'] = 'autotrainx'
os.environ['AUTOTRAINX_DB_PASSWORD'] = '1234'
```

---

## 👀 Visualización de Datos

### 1. VSCode con SQLTools

#### Instalación
1. Instalar extensiones:
   - SQLTools
   - SQLTools PostgreSQL Driver

#### Configuración
1. `Ctrl+Shift+P` → "SQLTools: Add New Connection"
2. Configurar:
   - Connection name: `AutoTrainX PostgreSQL`
   - Server: `localhost`
   - Port: `5432`
   - Database: `autotrainx`
   - Username: `autotrainx`
   - Password: `1234`

### 2. DBeaver

```bash
# Instalar
sudo snap install dbeaver-ce

# Configurar conexión similar a VSCode
```

### 3. Línea de Comandos

```bash
# Conectar
psql -h localhost -U autotrainx -d autotrainx

# Comandos útiles
\dt                    # Listar tablas
\d executions         # Ver estructura
SELECT * FROM executions LIMIT 10;  # Ver datos
\q                    # Salir
```

### 4. Sincronizar a SQLite (para visualización)

```bash
# Crear copia SQLite para ver con herramientas familiares
python database_utils/sync_to_sqlite.py

# Abrir con VSCode
code DB/executions_view.db
```

---

## 🛠️ Mantenimiento

### Estado del Servicio

```bash
# Ver estado
sudo systemctl status postgresql

# Iniciar/Detener/Reiniciar
sudo systemctl start postgresql
sudo systemctl stop postgresql
sudo systemctl restart postgresql
```

### Backup

```bash
# Backup completo
pg_dump -h localhost -U autotrainx autotrainx > backup_$(date +%Y%m%d).sql

# Restaurar
psql -h localhost -U autotrainx autotrainx < backup_20240802.sql
```

### Monitoreo

```bash
# Tamaño de base de datos
psql -h localhost -U autotrainx -d autotrainx -c \
  "SELECT pg_size_pretty(pg_database_size('autotrainx'));"

# Conexiones activas
psql -h localhost -U autotrainx -d autotrainx -c \
  "SELECT count(*) FROM pg_stat_activity;"
```

---

## ❗ Solución de Problemas

### Error: "FATAL: password authentication failed"

```bash
# Editar configuración
sudo nano /etc/postgresql/*/main/pg_hba.conf

# Cambiar esta línea:
local   all   all   peer
# Por:
local   all   all   md5

# Reiniciar
sudo systemctl restart postgresql
```

### Error: "database is locked" (no debería ocurrir con PostgreSQL)

```bash
# Ver procesos activos
psql -h localhost -U autotrainx -d autotrainx -c \
  "SELECT pid, usename, application_name, state \
   FROM pg_stat_activity WHERE state != 'idle';"
```

### PostgreSQL no inicia

```bash
# Ver logs
sudo journalctl -u postgresql -n 50

# Verificar puerto
sudo ss -tulpn | grep 5432
```

### Volver a SQLite

```bash
# Simplemente quitar las variables
unset AUTOTRAINX_DB_TYPE
unset AUTOTRAINX_DB_HOST
unset AUTOTRAINX_DB_PORT
unset AUTOTRAINX_DB_NAME
unset AUTOTRAINX_DB_USER
unset AUTOTRAINX_DB_PASSWORD
```

---

## 📜 Scripts de Utilidad

### 1. database_utils/setup_postgresql.sh - Instalación Automática

```bash
#!/bin/bash
# Guardar como: database_utils/setup_postgresql.sh

echo "🚀 Instalando PostgreSQL para AutoTrainX..."

# Instalar PostgreSQL
sudo apt update
sudo apt install -y postgresql postgresql-contrib

# Iniciar servicio
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Crear usuario y base de datos
sudo -u postgres psql << EOF
CREATE USER autotrainx WITH PASSWORD '1234';
CREATE DATABASE autotrainx OWNER autotrainx;
GRANT ALL PRIVILEGES ON DATABASE autotrainx TO autotrainx;
EOF

echo "✅ PostgreSQL instalado y configurado"
```

### 2. configure_autotrainx_pg.sh - Configuración Rápida

```bash
#!/bin/bash
# Guardar como: configure_autotrainx_pg.sh

echo "⚙️ Configurando AutoTrainX para PostgreSQL..."

# Backup de .bashrc
cp ~/.bashrc ~/.bashrc.backup

# Agregar configuración
cat >> ~/.bashrc << 'EOF'

# AutoTrainX PostgreSQL Configuration
export AUTOTRAINX_DB_TYPE=postgresql
export AUTOTRAINX_DB_HOST=localhost
export AUTOTRAINX_DB_PORT=5432
export AUTOTRAINX_DB_NAME=autotrainx
export AUTOTRAINX_DB_USER=autotrainx
export AUTOTRAINX_DB_PASSWORD=1234
EOF

echo "✅ Configuración agregada a .bashrc"
echo "📝 Ejecuta: source ~/.bashrc"
```

### 3. test_pg_connection.py - Verificar Conexión

```python
#!/usr/bin/env python3
import psycopg2

try:
    conn = psycopg2.connect(
        host="localhost",
        database="autotrainx",
        user="autotrainx",
        password="1234"
    )
    print("✅ Conexión exitosa a PostgreSQL")
    conn.close()
except Exception as e:
    print(f"❌ Error: {e}")
```

### 4. quick_stats.sh - Estadísticas Rápidas

```bash
#!/bin/bash
# Guardar como: quick_stats.sh

psql -h localhost -U autotrainx -d autotrainx << EOF
SELECT 
    'Total Executions' as metric, 
    COUNT(*) as value 
FROM executions
UNION ALL
SELECT 
    'Successful', 
    COUNT(*) 
FROM executions 
WHERE success = true
UNION ALL
SELECT 
    'Failed', 
    COUNT(*) 
FROM executions 
WHERE success = false;
EOF
```

---

## 📊 Consultas SQL Útiles

```sql
-- Últimas 10 ejecuciones
SELECT job_id, dataset_name, status, created_at 
FROM executions 
ORDER BY created_at DESC 
LIMIT 10;

-- Estadísticas por dataset
SELECT 
    dataset_name,
    COUNT(*) as total,
    SUM(CASE WHEN success THEN 1 ELSE 0 END) as exitosas,
    AVG(duration_seconds) as duracion_promedio
FROM executions
GROUP BY dataset_name
ORDER BY total DESC;

-- Ejecuciones en progreso
SELECT * FROM executions 
WHERE status IN ('training', 'pending')
ORDER BY created_at DESC;
```

---

## 🎯 Resumen de Comandos Rápidos

```bash
# Verificar PostgreSQL
sudo systemctl status postgresql

# Conectar a la base de datos
psql -h localhost -U autotrainx -d autotrainx

# Migrar datos
python database_utils/migrate_simple.py

# Verificar migración
python database_utils/verify_postgresql.py

# Ver datos en VSCode
# Usar SQLTools con la configuración proporcionada

# Backup rápido
pg_dump -h localhost -U autotrainx autotrainx > backup.sql
```

---

## 📝 Notas Importantes

1. **PostgreSQL debe estar siempre ejecutándose** cuando uses AutoTrainX
2. **La contraseña por defecto es '1234'** - cámbiala en producción
3. **Los datos NO se sincronizan automáticamente** entre SQLite y PostgreSQL
4. **Haz backups regulares** de tu base de datos

---

## 🆘 Soporte

Si encuentras problemas:
1. Revisa los logs: `sudo journalctl -u postgresql -n 50`
2. Verifica la conexión: `python test_pg_connection.py`
3. Consulta el estado: `sudo systemctl status postgresql`

Para volver a SQLite, simplemente elimina las variables de entorno de PostgreSQL.
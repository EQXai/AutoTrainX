#!/usr/bin/env python3
"""Verify PostgreSQL is working with AutoTrainX"""

import os

# Primero configurar las variables si no están
if not os.environ.get('AUTOTRAINX_DB_TYPE'):
    print("⚠️  Variables de entorno no configuradas. Configurando temporalmente...")
    os.environ['AUTOTRAINX_DB_TYPE'] = 'postgresql'
    os.environ['AUTOTRAINX_DB_HOST'] = 'localhost'
    os.environ['AUTOTRAINX_DB_PORT'] = '5432'
    os.environ['AUTOTRAINX_DB_NAME'] = 'autotrainx'
    os.environ['AUTOTRAINX_DB_USER'] = 'autotrainx'
    os.environ['AUTOTRAINX_DB_PASSWORD'] = '1234'

print("Configuración actual:")
print(f"  DB Type: {os.environ.get('AUTOTRAINX_DB_TYPE', 'not set')}")
print(f"  DB Host: {os.environ.get('AUTOTRAINX_DB_HOST', 'not set')}")
print(f"  DB Name: {os.environ.get('AUTOTRAINX_DB_NAME', 'not set')}")
print()

try:
    from src.database import DatabaseManager
    
    print("✅ Importación exitosa")
    
    # Crear manager
    db_manager = DatabaseManager()
    print(f"✅ Manager creado. Usando: {db_manager.config.db_type}")
    
    # Listar ejecuciones
    executions = db_manager.list_executions(limit=10)
    print(f"✅ Encontradas {len(executions)} ejecuciones")
    
    for exec in executions:
        print(f"   - {exec.job_id}: {exec.dataset_name} ({exec.status})")
    
    # Obtener estadísticas
    stats = db_manager.get_job_stats()
    print(f"\n📊 Estadísticas:")
    print(f"   Total ejecuciones: {stats['executions']['total']}")
    print(f"   Exitosas: {stats['executions']['success']}")
    print(f"   Fallidas: {stats['executions']['failed']}")
    
    print("\n✅ ¡PostgreSQL está funcionando correctamente!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
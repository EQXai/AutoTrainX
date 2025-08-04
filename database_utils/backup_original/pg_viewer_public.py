#!/usr/bin/env python3
"""
PostgreSQL Web Viewer with automatic public URL
Uses pyngrok to create public tunnel like Gradio
"""

import os
import psycopg2
from flask import Flask, render_template_string, jsonify
from datetime import datetime
import json
from pyngrok import ngrok
import threading
import time

app = Flask(__name__)

# Database configuration
DB_CONFIG = {
    'host': os.getenv('AUTOTRAINX_DB_HOST', 'localhost'),
    'port': os.getenv('AUTOTRAINX_DB_PORT', '5432'),
    'database': os.getenv('AUTOTRAINX_DB_NAME', 'autotrainx'),
    'user': os.getenv('AUTOTRAINX_DB_USER', 'autotrainx'),
    'password': os.getenv('AUTOTRAINX_DB_PASSWORD', '1234')
}

# HTML template with auto-refresh
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>PostgreSQL Viewer - {{ db_name }}</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f0f2f5;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .header h1 {
            margin: 0;
            font-size: 1.5rem;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 1rem;
        }
        .info-card {
            background: white;
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
        }
        .info-item {
            padding: 0.5rem;
            background: #f8f9fa;
            border-radius: 4px;
        }
        .info-label {
            font-size: 0.875rem;
            color: #6c757d;
        }
        .info-value {
            font-size: 1.125rem;
            font-weight: 600;
            color: #212529;
        }
        .table-selector {
            margin: 1rem 0;
            display: flex;
            gap: 1rem;
            flex-wrap: wrap;
            align-items: center;
        }
        select, button {
            padding: 0.5rem 1rem;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 1rem;
        }
        button {
            background: #667eea;
            color: white;
            border: none;
            cursor: pointer;
            transition: background 0.2s;
        }
        button:hover {
            background: #5a67d8;
        }
        .data-table {
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 0.75rem;
            text-align: left;
            border-bottom: 1px solid #e9ecef;
        }
        th {
            background: #f8f9fa;
            font-weight: 600;
            color: #495057;
            position: sticky;
            top: 0;
        }
        tr:hover {
            background-color: #f8f9fa;
        }
        .null {
            color: #6c757d;
            font-style: italic;
        }
        .loading {
            text-align: center;
            padding: 2rem;
            color: #6c757d;
        }
        .public-url {
            background: #28a745;
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            display: inline-block;
            margin: 0.5rem 0;
            font-weight: 600;
        }
        .refresh-info {
            text-align: right;
            color: #6c757d;
            font-size: 0.875rem;
            margin-top: 1rem;
        }
        @media (max-width: 768px) {
            .table-selector {
                flex-direction: column;
                align-items: stretch;
            }
            select, button {
                width: 100%;
            }
        }
    </style>
    <script>
        let autoRefresh = null;
        
        async function loadTable() {
            const table = document.getElementById('tableSelect').value;
            const container = document.getElementById('tableData');
            
            if (!table) {
                container.innerHTML = '<div class="loading">Select a table to view data</div>';
                return;
            }
            
            container.innerHTML = '<div class="loading">Loading...</div>';
            
            try {
                const response = await fetch(`/api/table/${table}`);
                const data = await response.json();
                
                if (data.error) {
                    container.innerHTML = `<div class="loading">Error: ${data.error}</div>`;
                    return;
                }
                
                let html = `<p style="margin: 1rem;">Total rows: ${data.row_count} | Showing: ${data.rows.length}</p>`;
                html += '<div style="overflow-x: auto;"><table>';
                
                // Headers
                html += '<thead><tr>';
                data.columns.forEach(col => {
                    html += `<th>${col}</th>`;
                });
                html += '</tr></thead><tbody>';
                
                // Rows
                data.rows.forEach(row => {
                    html += '<tr>';
                    row.forEach(cell => {
                        if (cell === null) {
                            html += '<td><span class="null">NULL</span></td>';
                        } else {
                            html += `<td>${cell}</td>`;
                        }
                    });
                    html += '</tr>';
                });
                
                html += '</tbody></table></div>';
                container.innerHTML = html;
                
                document.getElementById('refreshTime').textContent = new Date().toLocaleTimeString();
            } catch (error) {
                container.innerHTML = `<div class="loading">Error: ${error.message}</div>`;
            }
        }
        
        function toggleAutoRefresh() {
            const btn = document.getElementById('autoRefreshBtn');
            if (autoRefresh) {
                clearInterval(autoRefresh);
                autoRefresh = null;
                btn.textContent = 'Enable Auto-refresh';
            } else {
                autoRefresh = setInterval(loadTable, 5000);
                btn.textContent = 'Disable Auto-refresh';
            }
        }
        
        window.onload = function() {
            loadTable();
        };
    </script>
</head>
<body>
    <div class="header">
        <div class="container">
            <h1>🐘 PostgreSQL Database Viewer</h1>
            <div class="public-url">Public URL: {{ public_url }}</div>
        </div>
    </div>
    
    <div class="container">
        <div class="info-card">
            <div class="info-grid">
                <div class="info-item">
                    <div class="info-label">Database</div>
                    <div class="info-value">{{ db_name }}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Host</div>
                    <div class="info-value">{{ db_host }}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Tables</div>
                    <div class="info-value">{{ table_count }}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Size</div>
                    <div class="info-value">{{ db_size }}</div>
                </div>
            </div>
        </div>
        
        <div class="table-selector">
            <select id="tableSelect" onchange="loadTable()">
                <option value="">Select a table...</option>
                {% for table in tables %}
                <option value="{{ table }}">{{ table }}</option>
                {% endfor %}
            </select>
            <button onclick="loadTable()">Refresh Data</button>
            <button id="autoRefreshBtn" onclick="toggleAutoRefresh()">Enable Auto-refresh</button>
        </div>
        
        <div class="data-table" id="tableData">
            <div class="loading">Select a table to view data</div>
        </div>
        
        <div class="refresh-info">
            Last refresh: <span id="refreshTime">-</span>
        </div>
    </div>
</body>
</html>
'''

# Global variable for public URL
PUBLIC_URL = None

def get_db_connection():
    """Create database connection"""
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        return None

def format_value(value):
    """Format values for JSON serialization"""
    if isinstance(value, datetime):
        return value.strftime('%Y-%m-%d %H:%M:%S')
    elif isinstance(value, (dict, list)):
        return json.dumps(value)
    elif value is None:
        return None
    return str(value)

@app.route('/')
def index():
    """Main page"""
    conn = get_db_connection()
    if not conn:
        return "Cannot connect to database", 500
    
    try:
        cur = conn.cursor()
        
        # Get tables
        cur.execute("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public' 
            ORDER BY tablename
        """)
        tables = [row[0] for row in cur.fetchall()]
        
        # Get database size
        cur.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
        db_size = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        
        return render_template_string(HTML_TEMPLATE,
                                    tables=tables,
                                    table_count=len(tables),
                                    db_name=DB_CONFIG['database'],
                                    db_host=DB_CONFIG['host'],
                                    db_size=db_size,
                                    public_url=PUBLIC_URL or "Creating...")
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/api/table/<table_name>')
def get_table_data(table_name):
    """API endpoint for table data"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Cannot connect to database'})
    
    try:
        cur = conn.cursor()
        
        # Validate table name
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM pg_tables 
                WHERE schemaname = 'public' 
                AND tablename = %s
            )
        """, (table_name,))
        
        if not cur.fetchone()[0]:
            return jsonify({'error': f"Table '{table_name}' not found"})
        
        # Get row count
        cur.execute(f"SELECT COUNT(*) FROM {table_name}")
        row_count = cur.fetchone()[0]
        
        # Get column names
        cur.execute(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = %s 
            ORDER BY ordinal_position
        """, (table_name,))
        columns = [row[0] for row in cur.fetchall()]
        
        # Get data
        limit = 100
        cur.execute(f"SELECT * FROM {table_name} ORDER BY 1 DESC LIMIT %s", (limit,))
        rows = []
        for row in cur.fetchall():
            formatted_row = [format_value(cell) for cell in row]
            rows.append(formatted_row)
        
        cur.close()
        conn.close()
        
        return jsonify({
            'columns': columns,
            'rows': rows,
            'row_count': row_count
        })
    except Exception as e:
        return jsonify({'error': str(e)})

def start_ngrok():
    """Start ngrok tunnel and get public URL"""
    global PUBLIC_URL
    try:
        # Kill any existing ngrok processes
        ngrok.kill()
        
        # Start ngrok tunnel
        tunnel = ngrok.connect(5000, bind_tls=True)
        PUBLIC_URL = tunnel.public_url
        print(f"\n{'='*60}")
        print(f"🌐 Public URL created successfully!")
        print(f"📱 Access from anywhere: {PUBLIC_URL}")
        print(f"{'='*60}\n")
    except Exception as e:
        print(f"Error creating public URL: {e}")
        PUBLIC_URL = "Error creating public URL"

if __name__ == '__main__':
    # Load .env file if exists
    env_file = os.path.join(os.path.dirname(__file__), '..', 'settings', '.env')
    if os.path.exists(env_file):
        print(f"Loading configuration from {env_file}")
        with open(env_file) as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
        
        # Update DB_CONFIG
        DB_CONFIG.update({
            'host': os.getenv('AUTOTRAINX_DB_HOST', 'localhost'),
            'port': os.getenv('AUTOTRAINX_DB_PORT', '5432'),
            'database': os.getenv('AUTOTRAINX_DB_NAME', 'autotrainx'),
            'user': os.getenv('AUTOTRAINX_DB_USER', 'autotrainx'),
            'password': os.getenv('AUTOTRAINX_DB_PASSWORD', '1234')
        })
    
    print(f"Starting PostgreSQL Web Viewer with public URL...")
    print(f"Database: {DB_CONFIG['database']} @ {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    
    # Start ngrok in a separate thread
    ngrok_thread = threading.Thread(target=start_ngrok)
    ngrok_thread.daemon = True
    ngrok_thread.start()
    
    # Give ngrok time to start
    time.sleep(2)
    
    # Start Flask
    app.run(host='0.0.0.0', port=5000, debug=False)
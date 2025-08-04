#!/usr/bin/env python3
"""
Simple PostgreSQL Web Viewer
Provides a web interface to view PostgreSQL tables
"""

import os
import psycopg2
from flask import Flask, render_template_string
from datetime import datetime
import json

app = Flask(__name__)

# Database configuration - reads from environment or .env file
DB_CONFIG = {
    'host': os.getenv('AUTOTRAINX_DB_HOST', 'localhost'),
    'port': os.getenv('AUTOTRAINX_DB_PORT', '5432'),
    'database': os.getenv('AUTOTRAINX_DB_NAME', 'autotrainx'),
    'user': os.getenv('AUTOTRAINX_DB_USER', 'autotrainx'),
    'password': os.getenv('AUTOTRAINX_DB_PASSWORD', '1234')
}

# HTML template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>PostgreSQL Viewer - {{ db_name }}</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 10px;
        }
        h2 {
            color: #666;
            margin-top: 30px;
        }
        .info {
            background-color: #e8f5e9;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .error {
            background-color: #ffebee;
            color: #c62828;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        th {
            background-color: #4CAF50;
            color: white;
            font-weight: bold;
        }
        tr:nth-child(even) {
            background-color: #f2f2f2;
        }
        tr:hover {
            background-color: #e8f5e9;
        }
        .table-list {
            margin-bottom: 30px;
        }
        .table-link {
            display: inline-block;
            margin: 5px;
            padding: 8px 15px;
            background-color: #2196F3;
            color: white;
            text-decoration: none;
            border-radius: 4px;
        }
        .table-link:hover {
            background-color: #1976D2;
        }
        .nav {
            margin-bottom: 20px;
        }
        .nav a {
            margin-right: 10px;
            color: #2196F3;
        }
        .timestamp {
            color: #666;
            font-size: 0.9em;
        }
        .null {
            color: #999;
            font-style: italic;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>PostgreSQL Database Viewer</h1>
        
        <div class="info">
            <strong>Database:</strong> {{ db_name }} | 
            <strong>Host:</strong> {{ db_host }} | 
            <strong>User:</strong> {{ db_user }} |
            <strong>Updated:</strong> <span class="timestamp">{{ timestamp }}</span>
        </div>
        
        <div class="nav">
            <a href="/">Home</a> |
            <a href="/tables">All Tables</a> |
            <a href="/status">Database Status</a>
        </div>
        
        {% if error %}
        <div class="error">Error: {{ error }}</div>
        {% endif %}
        
        {% block content %}{% endblock %}
    </div>
</body>
</html>
'''

HOME_TEMPLATE = HTML_TEMPLATE + '''
{% block content %}
<h2>Available Tables</h2>
<div class="table-list">
    {% for table in tables %}
    <a href="/table/{{ table }}" class="table-link">{{ table }}</a>
    {% endfor %}
</div>

<h2>Database Statistics</h2>
<table>
    <tr>
        <th>Metric</th>
        <th>Value</th>
    </tr>
    {% for stat in stats %}
    <tr>
        <td>{{ stat[0] }}</td>
        <td>{{ stat[1] }}</td>
    </tr>
    {% endfor %}
</table>
{% endblock %}
'''

TABLE_TEMPLATE = HTML_TEMPLATE + '''
{% block content %}
<h2>Table: {{ table_name }}</h2>

<p><strong>Total Records:</strong> {{ row_count }}</p>

<table>
    <thead>
        <tr>
            {% for column in columns %}
            <th>{{ column }}</th>
            {% endfor %}
        </tr>
    </thead>
    <tbody>
        {% for row in rows %}
        <tr>
            {% for cell in row %}
            <td>
                {% if cell is none %}
                    <span class="null">NULL</span>
                {% else %}
                    {{ cell }}
                {% endif %}
            </td>
            {% endfor %}
        </tr>
        {% endfor %}
    </tbody>
</table>

{% if row_count > limit %}
<p><em>Showing first {{ limit }} of {{ row_count }} records</em></p>
{% endif %}
{% endblock %}
'''

def get_db_connection():
    """Create database connection"""
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        return None

def format_value(value):
    """Format values for display"""
    if isinstance(value, datetime):
        return value.strftime('%Y-%m-%d %H:%M:%S')
    elif isinstance(value, (dict, list)):
        return json.dumps(value)
    return value

@app.route('/')
def index():
    """Home page with table list and stats"""
    conn = get_db_connection()
    if not conn:
        return render_template_string(HOME_TEMPLATE, 
                                    error="Cannot connect to database",
                                    tables=[],
                                    stats=[],
                                    db_name=DB_CONFIG['database'],
                                    db_host=DB_CONFIG['host'],
                                    db_user=DB_CONFIG['user'],
                                    timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
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
        
        # Get database stats
        stats = []
        
        # Database size
        cur.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
        stats.append(('Database Size', cur.fetchone()[0]))
        
        # Number of tables
        stats.append(('Number of Tables', len(tables)))
        
        # Total connections
        cur.execute("SELECT count(*) FROM pg_stat_activity")
        stats.append(('Active Connections', cur.fetchone()[0]))
        
        # PostgreSQL version
        cur.execute("SELECT version()")
        version = cur.fetchone()[0].split(' ')[1]
        stats.append(('PostgreSQL Version', version))
        
        cur.close()
        conn.close()
        
        return render_template_string(HOME_TEMPLATE,
                                    tables=tables,
                                    stats=stats,
                                    error=None,
                                    db_name=DB_CONFIG['database'],
                                    db_host=DB_CONFIG['host'],
                                    db_user=DB_CONFIG['user'],
                                    timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    except Exception as e:
        return render_template_string(HOME_TEMPLATE,
                                    error=str(e),
                                    tables=[],
                                    stats=[],
                                    db_name=DB_CONFIG['database'],
                                    db_host=DB_CONFIG['host'],
                                    db_user=DB_CONFIG['user'],
                                    timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

@app.route('/table/<table_name>')
def view_table(table_name):
    """View specific table contents"""
    conn = get_db_connection()
    if not conn:
        return render_template_string(TABLE_TEMPLATE,
                                    error="Cannot connect to database",
                                    table_name=table_name,
                                    columns=[],
                                    rows=[],
                                    row_count=0,
                                    limit=100,
                                    db_name=DB_CONFIG['database'],
                                    db_host=DB_CONFIG['host'],
                                    db_user=DB_CONFIG['user'],
                                    timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    try:
        cur = conn.cursor()
        
        # Validate table name (prevent SQL injection)
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM pg_tables 
                WHERE schemaname = 'public' 
                AND tablename = %s
            )
        """, (table_name,))
        
        if not cur.fetchone()[0]:
            raise Exception(f"Table '{table_name}' not found")
        
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
        
        # Get data (limit to 100 rows for performance)
        limit = 100
        cur.execute(f"SELECT * FROM {table_name} ORDER BY 1 DESC LIMIT %s", (limit,))
        rows = []
        for row in cur.fetchall():
            formatted_row = [format_value(cell) for cell in row]
            rows.append(formatted_row)
        
        cur.close()
        conn.close()
        
        return render_template_string(TABLE_TEMPLATE,
                                    table_name=table_name,
                                    columns=columns,
                                    rows=rows,
                                    row_count=row_count,
                                    limit=limit,
                                    error=None,
                                    db_name=DB_CONFIG['database'],
                                    db_host=DB_CONFIG['host'],
                                    db_user=DB_CONFIG['user'],
                                    timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    except Exception as e:
        return render_template_string(TABLE_TEMPLATE,
                                    error=str(e),
                                    table_name=table_name,
                                    columns=[],
                                    rows=[],
                                    row_count=0,
                                    limit=100,
                                    db_name=DB_CONFIG['database'],
                                    db_host=DB_CONFIG['host'],
                                    db_user=DB_CONFIG['user'],
                                    timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

@app.route('/tables')
def all_tables():
    """Show all tables with details"""
    return index()

@app.route('/status')
def status():
    """Database status page"""
    conn = get_db_connection()
    if conn:
        conn.close()
        status = "Connected"
    else:
        status = "Disconnected"
    
    return f"""
    <h1>Database Status</h1>
    <p>Status: {status}</p>
    <p>Configuration:</p>
    <ul>
        <li>Host: {DB_CONFIG['host']}</li>
        <li>Port: {DB_CONFIG['port']}</li>
        <li>Database: {DB_CONFIG['database']}</li>
        <li>User: {DB_CONFIG['user']}</li>
    </ul>
    <p><a href="/">Back to Home</a></p>
    """

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
        
        # Update DB_CONFIG with loaded values
        DB_CONFIG.update({
            'host': os.getenv('AUTOTRAINX_DB_HOST', 'localhost'),
            'port': os.getenv('AUTOTRAINX_DB_PORT', '5432'),
            'database': os.getenv('AUTOTRAINX_DB_NAME', 'autotrainx'),
            'user': os.getenv('AUTOTRAINX_DB_USER', 'autotrainx'),
            'password': os.getenv('AUTOTRAINX_DB_PASSWORD', '1234')
        })
    
    print(f"Starting PostgreSQL Web Viewer")
    print(f"Database: {DB_CONFIG['database']} @ {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print(f"Access at: http://0.0.0.0:5000")
    
    app.run(host='0.0.0.0', port=5000, debug=False)
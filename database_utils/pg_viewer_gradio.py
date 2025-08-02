#!/usr/bin/env python3
"""
PostgreSQL Viewer with Gradio - Public URL
Automatically creates a public shareable link
"""

import os
import gradio as gr
import psycopg2
import pandas as pd
from datetime import datetime

# Database configuration
DB_CONFIG = {
    'host': os.getenv('AUTOTRAINX_DB_HOST', 'localhost'),
    'port': os.getenv('AUTOTRAINX_DB_PORT', '5432'),
    'database': os.getenv('AUTOTRAINX_DB_NAME', 'autotrainx'),
    'user': os.getenv('AUTOTRAINX_DB_USER', 'autotrainx'),
    'password': os.getenv('AUTOTRAINX_DB_PASSWORD', '1234')
}

def load_env():
    """Load .env file if exists"""
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
        
        # Update config
        DB_CONFIG.update({
            'host': os.getenv('AUTOTRAINX_DB_HOST', 'localhost'),
            'port': os.getenv('AUTOTRAINX_DB_PORT', '5432'),
            'database': os.getenv('AUTOTRAINX_DB_NAME', 'autotrainx'),
            'user': os.getenv('AUTOTRAINX_DB_USER', 'autotrainx'),
            'password': os.getenv('AUTOTRAINX_DB_PASSWORD', '1234')
        })

def get_connection():
    """Create database connection"""
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        return None

def get_tables():
    """Get list of tables"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public' 
            ORDER BY tablename
        """)
        tables = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()
        return tables
    except:
        return []

def get_table_data(table_name, limit=100):
    """Get table data as dataframe"""
    if not table_name:
        return pd.DataFrame(), "Please select a table"
    
    conn = get_connection()
    if not conn:
        return pd.DataFrame(), "Cannot connect to database"
    
    try:
        # Get total count
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM {table_name}")
        total_count = cur.fetchone()[0]
        cur.close()
        
        # Get data
        query = f"SELECT * FROM {table_name} ORDER BY 1 DESC LIMIT {limit}"
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        info = f"Table: {table_name} | Total rows: {total_count} | Showing: {len(df)}"
        return df, info
    except Exception as e:
        return pd.DataFrame(), f"Error: {str(e)}"

def get_database_info():
    """Get database information"""
    conn = get_connection()
    if not conn:
        return "Cannot connect to database"
    
    try:
        cur = conn.cursor()
        info_list = []
        
        # Database info
        info_list.append(f"**Database:** {DB_CONFIG['database']}")
        info_list.append(f"**Host:** {DB_CONFIG['host']}")
        info_list.append(f"**Port:** {DB_CONFIG['port']}")
        info_list.append(f"**User:** {DB_CONFIG['user']}")
        
        # Database size
        cur.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
        size = cur.fetchone()[0]
        info_list.append(f"**Size:** {size}")
        
        # Table count
        cur.execute("SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'public'")
        table_count = cur.fetchone()[0]
        info_list.append(f"**Tables:** {table_count}")
        
        # PostgreSQL version
        cur.execute("SELECT version()")
        version = cur.fetchone()[0].split(' ')[1]
        info_list.append(f"**PostgreSQL:** {version}")
        
        cur.close()
        conn.close()
        
        return "\n\n".join(info_list)
    except Exception as e:
        return f"Error: {str(e)}"

def run_custom_query(query):
    """Run custom SQL query"""
    if not query.strip():
        return pd.DataFrame(), "Please enter a query"
    
    # Basic safety check (prevent destructive operations)
    forbidden = ['DROP', 'DELETE', 'TRUNCATE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE']
    query_upper = query.upper()
    for word in forbidden:
        if word in query_upper:
            return pd.DataFrame(), f"Query contains forbidden operation: {word}"
    
    conn = get_connection()
    if not conn:
        return pd.DataFrame(), "Cannot connect to database"
    
    try:
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df, f"Query executed successfully. Rows returned: {len(df)}"
    except Exception as e:
        return pd.DataFrame(), f"Error: {str(e)}"

# Load environment
load_env()

# Create Gradio interface
with gr.Blocks(title="PostgreSQL Viewer") as app:
    gr.Markdown("# 🐘 PostgreSQL Database Viewer")
    gr.Markdown("View your PostgreSQL database tables with a public shareable link")
    
    with gr.Tab("Database Info"):
        info_button = gr.Button("Refresh Database Info", variant="primary")
        db_info = gr.Markdown(get_database_info())
        
        def update_info():
            return get_database_info()
        
        info_button.click(update_info, outputs=db_info)
    
    with gr.Tab("Table Viewer"):
        with gr.Row():
            table_dropdown = gr.Dropdown(
                choices=get_tables(),
                label="Select Table",
                interactive=True
            )
            limit_slider = gr.Slider(
                minimum=10,
                maximum=1000,
                value=100,
                step=10,
                label="Row Limit"
            )
            refresh_btn = gr.Button("Refresh Tables")
        
        table_info = gr.Markdown()
        table_data = gr.DataFrame(
            label="Table Data",
            interactive=False,
            wrap=True
        )
        
        def refresh_tables():
            return gr.Dropdown(choices=get_tables())
        
        def load_table(table_name, limit):
            df, info = get_table_data(table_name, limit)
            return df, info
        
        refresh_btn.click(refresh_tables, outputs=table_dropdown)
        table_dropdown.change(
            load_table,
            inputs=[table_dropdown, limit_slider],
            outputs=[table_data, table_info]
        )
        limit_slider.change(
            load_table,
            inputs=[table_dropdown, limit_slider],
            outputs=[table_data, table_info]
        )
    
    with gr.Tab("Custom Query"):
        gr.Markdown("⚠️ **Read-only mode** - Only SELECT queries are allowed")
        
        query_input = gr.Textbox(
            label="SQL Query",
            placeholder="SELECT * FROM table_name LIMIT 10",
            lines=3
        )
        query_btn = gr.Button("Execute Query", variant="primary")
        query_info = gr.Markdown()
        query_result = gr.DataFrame(
            label="Query Result",
            interactive=False,
            wrap=True
        )
        
        query_btn.click(
            run_custom_query,
            inputs=query_input,
            outputs=[query_result, query_info]
        )
    
    gr.Markdown(f"---\n*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

# Launch with public URL
if __name__ == "__main__":
    print("Starting PostgreSQL Viewer with Gradio...")
    print(f"Database: {DB_CONFIG['database']} @ {DB_CONFIG['host']}")
    print("\nCreating public URL...")
    
    # Launch with share=True for public URL
    app.launch(
        share=True,  # This creates the public URL
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True
    )
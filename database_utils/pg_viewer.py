#!/usr/bin/env python3
"""
PostgreSQL Database Viewer for AutoTrainX
Simple Gradio interface for viewing database tables
"""

import os
import sys
import gradio as gr
import psycopg2
import pandas as pd
from datetime import datetime
from pathlib import Path

# Database configuration
DB_CONFIG = {
    'host': os.getenv('AUTOTRAINX_DB_HOST', 'localhost'),
    'port': os.getenv('AUTOTRAINX_DB_PORT', '5432'),
    'database': os.getenv('AUTOTRAINX_DB_NAME', 'autotrainx'),
    'user': os.getenv('AUTOTRAINX_DB_USER', 'autotrainx'),
    'password': os.getenv('AUTOTRAINX_DB_PASSWORD', '1234')
}

def get_connection():
    """Create database connection"""
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        print(f"Connection error: {e}")
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
        conn.close()
        return tables
    except Exception as e:
        print(f"Error getting tables: {e}")
        return []

def get_table_info(table_name):
    """Get table information"""
    if not table_name:
        return "Select a table", None
    
    conn = get_connection()
    if not conn:
        return "Connection failed", None
    
    try:
        cur = conn.cursor()
        
        # Get row count
        cur.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cur.fetchone()[0]
        
        # Get column info
        cur.execute("""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = %s
            ORDER BY ordinal_position
        """, (table_name,))
        
        columns = cur.fetchall()
        
        info = f"**Table: {table_name}**\n"
        info += f"Total rows: {count:,}\n\n"
        info += "**Columns:**\n"
        
        for col_name, data_type, max_length in columns:
            if max_length:
                info += f"- {col_name} ({data_type}({max_length}))\n"
            else:
                info += f"- {col_name} ({data_type})\n"
        
        conn.close()
        return info, count
        
    except Exception as e:
        return f"Error: {e}", None

def view_table_data(table_name, limit=100, offset=0, order_by=None, order_desc=False):
    """View table data with pagination"""
    if not table_name:
        return pd.DataFrame({"Message": ["Select a table to view"]})
    
    conn = get_connection()
    if not conn:
        return pd.DataFrame({"Error": ["Connection failed"]})
    
    try:
        # Build query
        query = f"SELECT * FROM {table_name}"
        
        if order_by:
            query += f" ORDER BY {order_by}"
            if order_desc:
                query += " DESC"
        
        query += f" LIMIT {limit} OFFSET {offset}"
        
        # Get data
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        return df
        
    except Exception as e:
        return pd.DataFrame({"Error": [str(e)]})

def export_table(table_name, format="csv"):
    """Export table to file"""
    if not table_name:
        return None, "Select a table to export"
    
    conn = get_connection()
    if not conn:
        return None, "Connection failed"
    
    try:
        # Get all data
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        conn.close()
        
        # Create export directory
        export_dir = Path("exports")
        export_dir.mkdir(exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format == "csv":
            filename = export_dir / f"{table_name}_{timestamp}.csv"
            df.to_csv(filename, index=False)
        elif format == "excel":
            filename = export_dir / f"{table_name}_{timestamp}.xlsx"
            df.to_excel(filename, index=False)
        elif format == "json":
            filename = export_dir / f"{table_name}_{timestamp}.json"
            df.to_json(filename, orient="records", indent=2)
        
        return str(filename), f"Exported {len(df)} rows to {filename}"
        
    except Exception as e:
        return None, f"Export error: {e}"

def search_table(table_name, search_term, column=None):
    """Search within a table"""
    if not table_name or not search_term:
        return pd.DataFrame({"Message": ["Enter table name and search term"]})
    
    conn = get_connection()
    if not conn:
        return pd.DataFrame({"Error": ["Connection failed"]})
    
    try:
        cur = conn.cursor()
        
        if column:
            # Search in specific column
            query = f"""
                SELECT * FROM {table_name} 
                WHERE {column}::text ILIKE %s
                LIMIT 100
            """
        else:
            # Search in all columns
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = %s
            """, (table_name,))
            columns = [row[0] for row in cur.fetchall()]
            
            conditions = [f"{col}::text ILIKE %s" for col in columns]
            query = f"""
                SELECT * FROM {table_name} 
                WHERE {' OR '.join(conditions)}
                LIMIT 100
            """
            search_term = [f"%{search_term}%"] * len(columns)
        
        df = pd.read_sql_query(query, conn, params=search_term if column else search_term)
        conn.close()
        
        return df
        
    except Exception as e:
        return pd.DataFrame({"Error": [str(e)]})

# Create Gradio interface
with gr.Blocks(title="AutoTrainX Database Viewer", theme=gr.themes.Base()) as app:
    gr.Markdown("# AutoTrainX PostgreSQL Database Viewer")
    
    with gr.Row():
        gr.Markdown(f"""
        **Connection:** {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}  
        **User:** {DB_CONFIG['user']}
        """)
    
    with gr.Tab("Browse Tables"):
        with gr.Row():
            with gr.Column(scale=1):
                table_dropdown = gr.Dropdown(
                    choices=get_tables(),
                    label="Select Table",
                    interactive=True
                )
                refresh_btn = gr.Button("🔄 Refresh Tables", size="sm")
                
                table_info = gr.Markdown("Select a table to view information")
                
            with gr.Column(scale=3):
                with gr.Row():
                    limit_input = gr.Number(value=100, label="Rows per page", minimum=1, maximum=10000)
                    offset_input = gr.Number(value=0, label="Offset", minimum=0)
                    order_dropdown = gr.Dropdown(label="Order by", interactive=True)
                    order_desc = gr.Checkbox(label="Descending", value=False)
                
                view_btn = gr.Button("View Data", variant="primary")
                
                data_output = gr.Dataframe(
                    label="Table Data",
                    interactive=False,
                    wrap=True
                )
                
                with gr.Row():
                    prev_btn = gr.Button("← Previous", size="sm")
                    page_info = gr.Markdown("Page 1")
                    next_btn = gr.Button("Next →", size="sm")
    
    with gr.Tab("Search"):
        with gr.Row():
            search_table_dropdown = gr.Dropdown(
                choices=get_tables(),
                label="Table to search",
                interactive=True
            )
            search_column = gr.Dropdown(
                label="Column (optional)",
                interactive=True
            )
        
        search_input = gr.Textbox(
            label="Search term",
            placeholder="Enter search term..."
        )
        
        search_btn = gr.Button("🔍 Search", variant="primary")
        
        search_results = gr.Dataframe(
            label="Search Results",
            interactive=False,
            wrap=True
        )
    
    with gr.Tab("Export"):
        with gr.Row():
            export_table_dropdown = gr.Dropdown(
                choices=get_tables(),
                label="Table to export",
                interactive=True
            )
            export_format = gr.Radio(
                choices=["csv", "excel", "json"],
                value="csv",
                label="Export format"
            )
        
        export_btn = gr.Button("📥 Export Table", variant="primary")
        
        export_output = gr.File(label="Download exported file")
        export_status = gr.Markdown("")
    
    # Event handlers
    def update_table_info(table_name):
        info, count = get_table_info(table_name)
        if count is not None:
            # Get columns for ordering
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = %s
                ORDER BY ordinal_position
            """, (table_name,))
            columns = [row[0] for row in cur.fetchall()]
            conn.close()
            
            return info, gr.Dropdown(choices=columns)
        return info, gr.Dropdown(choices=[])
    
    def update_offset(direction, current_offset, limit):
        if direction == "next":
            return current_offset + limit
        else:
            return max(0, current_offset - limit)
    
    def update_page_info(offset, limit):
        page = (offset // limit) + 1
        return f"Page {page} (showing rows {offset + 1}-{offset + limit})"
    
    # Connect events
    table_dropdown.change(
        update_table_info,
        inputs=[table_dropdown],
        outputs=[table_info, order_dropdown]
    )
    
    view_btn.click(
        view_table_data,
        inputs=[table_dropdown, limit_input, offset_input, order_dropdown, order_desc],
        outputs=data_output
    )
    
    next_btn.click(
        lambda o, l: update_offset("next", o, l),
        inputs=[offset_input, limit_input],
        outputs=offset_input
    ).then(
        view_table_data,
        inputs=[table_dropdown, limit_input, offset_input, order_dropdown, order_desc],
        outputs=data_output
    ).then(
        update_page_info,
        inputs=[offset_input, limit_input],
        outputs=page_info
    )
    
    prev_btn.click(
        lambda o, l: update_offset("prev", o, l),
        inputs=[offset_input, limit_input],
        outputs=offset_input
    ).then(
        view_table_data,
        inputs=[table_dropdown, limit_input, offset_input, order_dropdown, order_desc],
        outputs=data_output
    ).then(
        update_page_info,
        inputs=[offset_input, limit_input],
        outputs=page_info
    )
    
    refresh_btn.click(
        lambda: gr.Dropdown(choices=get_tables()),
        outputs=table_dropdown
    )
    
    # Search events
    search_table_dropdown.change(
        lambda t: gr.Dropdown(choices=get_table_info(t)[1].choices if t else []),
        inputs=[search_table_dropdown],
        outputs=search_column
    )
    
    search_btn.click(
        search_table,
        inputs=[search_table_dropdown, search_input, search_column],
        outputs=search_results
    )
    
    # Export events
    export_btn.click(
        export_table,
        inputs=[export_table_dropdown, export_format],
        outputs=[export_output, export_status]
    )

if __name__ == "__main__":
    print("Starting AutoTrainX Database Viewer...")
    print(f"Database: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    print("\nThe browser will open automatically with a shareable link.")
    print("Press Ctrl+C to stop the server.\n")
    
    app.launch(share=True, inbrowser=True)
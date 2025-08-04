#!/usr/bin/env python3
import psycopg2
import os
import sys
from tabulate import tabulate
from datetime import datetime
import getpass
from blessed import Terminal

class PostgreSQLControlPanel:
    def __init__(self):
        self.connection = None
        self.cursor = None
        self.term = Terminal()
        
    def connect(self, host='localhost', port=5432, database='postgres', 
                user=None, password=None):
        """Connect to PostgreSQL"""
        try:
            if not user:
                user = input("PostgreSQL user: ")
            if not password:
                password = getpass.getpass("Password: ")
                
            self.connection = psycopg2.connect(
                host=host,
                port=port,
                database=database,
                user=user,
                password=password
            )
            self.cursor = self.connection.cursor()
            print(f"\n✓ Connected to {database}@{host}:{port}")
            return True
        except Exception as e:
            print(f"\n✗ Connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from PostgreSQL"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        print("\n✓ Disconnected")
    
    def clear_screen(self):
        """Clear screen"""
        print(self.term.clear())
    
    def show_databases(self):
        """Show all databases"""
        try:
            self.cursor.execute("""
                SELECT datname, pg_database_size(datname) as size, 
                       pg_size_pretty(pg_database_size(datname)) as size_pretty
                FROM pg_database 
                WHERE datistemplate = false
                ORDER BY size DESC
            """)
            
            databases = self.cursor.fetchall()
            headers = ['Database', 'Size (bytes)', 'Size']
            print("\n=== DATABASES ===")
            print(tabulate(databases, headers=headers, tablefmt='grid'))
        except Exception as e:
            print(f"\n✗ Error: {e}")
    
    def show_tables(self, schema='public'):
        """Show tables in current database"""
        try:
            # First get tables without count
            self.cursor.execute(f"""
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
                FROM pg_tables
                WHERE schemaname = '{schema}'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
            """)
            
            tables = []
            for row in self.cursor.fetchall():
                schema_name, table_name, size = row
                # Get row count individually
                try:
                    self.cursor.execute(f'SELECT COUNT(*) FROM "{schema_name}"."{table_name}"')
                    count = self.cursor.fetchone()[0]
                except:
                    count = 'N/A'
                tables.append([schema_name, table_name, size, count])
            
            headers = ['Schema', 'Table', 'Size', 'Rows']
            print(f"\n=== TABLES IN {self.connection.info.dbname} ===")
            print(tabulate(tables, headers=headers, tablefmt='grid'))
        except Exception as e:
            print(f"\n✗ Error: {e}")
    
    def show_active_connections(self):
        """Show active connections"""
        try:
            self.cursor.execute("""
                SELECT 
                    pid,
                    usename,
                    datname,
                    client_addr,
                    application_name,
                    state,
                    query_start
                FROM pg_stat_activity
                WHERE state != 'idle'
                ORDER BY query_start DESC
            """)
            
            connections = self.cursor.fetchall()
            headers = ['PID', 'User', 'Database', 'Client', 'Application', 'State', 'Query Start']
            print("\n=== ACTIVE CONNECTIONS ===")
            print(tabulate(connections, headers=headers, tablefmt='grid'))
        except Exception as e:
            print(f"\n✗ Error: {e}")
    
    def execute_query(self):
        """Execute custom SQL query"""
        self.clear_screen()
        print("=== EXECUTE SQL QUERY ===")
        print("(Type 'exit' to quit)\n")
        
        query = []
        while True:
            line = input("SQL> ")
            if line.lower() == 'exit':
                return
            query.append(line)
            if line.strip().endswith(';'):
                break
        
        full_query = '\n'.join(query)
        
        try:
            self.cursor.execute(full_query)
            
            # If SELECT, show results
            if full_query.strip().upper().startswith('SELECT'):
                results = self.cursor.fetchall()
                if results:
                    headers = [desc[0] for desc in self.cursor.description]
                    print("\n" + tabulate(results, headers=headers, tablefmt='grid'))
                else:
                    print("\n✓ No results")
            else:
                self.connection.commit()
                print(f"\n✓ Query executed. Affected rows: {self.cursor.rowcount}")
                
        except Exception as e:
            self.connection.rollback()
            print(f"\n✗ Error: {e}")
    
    def show_table_structure(self):
        """Show table structure"""
        self.clear_screen()
        print("=== VIEW TABLE STRUCTURE ===\n")
        table_name = input("Table name: ")
        schema = input("Schema (default: public): ") or 'public'
        
        try:
            self.cursor.execute(f"""
                SELECT 
                    column_name,
                    data_type,
                    character_maximum_length,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_schema = '{schema}' 
                AND table_name = '{table_name}'
                ORDER BY ordinal_position
            """)
            
            columns = self.cursor.fetchall()
            if columns:
                headers = ['Column', 'Type', 'Max Length', 'Nullable', 'Default']
                print(f"\n=== STRUCTURE OF {schema}.{table_name} ===")
                print(tabulate(columns, headers=headers, tablefmt='grid'))
                
                # Show indexes
                self.cursor.execute(f"""
                    SELECT indexname, indexdef 
                    FROM pg_indexes 
                    WHERE schemaname = '{schema}' 
                    AND tablename = '{table_name}'
                """)
                
                indexes = self.cursor.fetchall()
                if indexes:
                    print("\n=== INDEXES ===")
                    for idx_name, idx_def in indexes:
                        print(f"• {idx_name}: {idx_def}")
            else:
                print(f"\n✗ Table {schema}.{table_name} not found")
                
        except Exception as e:
            print(f"\n✗ Error: {e}")
    
    def backup_database(self):
        """Create database backup"""
        self.clear_screen()
        db_name = self.connection.info.dbname
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f"{db_name}_backup_{timestamp}.sql"
        
        print(f"=== BACKUP {db_name} ===\n")
        
        # Need credentials for pg_dump
        host = self.connection.info.host or 'localhost'
        port = self.connection.info.port
        user = self.connection.info.user
        
        password = getpass.getpass("Password for pg_dump: ")
        
        cmd = f"PGPASSWORD='{password}' pg_dump -h {host} -p {port} -U {user} -d {db_name} > {backup_file}"
        
        result = os.system(cmd)
        if result == 0:
            print(f"\n✓ Backup created: {backup_file}")
        else:
            print("\n✗ Error creating backup")
    
    def show_statistics(self):
        """Show database statistics"""
        try:
            self.clear_screen()
            # Total DB size
            self.cursor.execute(f"""
                SELECT pg_size_pretty(pg_database_size('{self.connection.info.dbname}'))
            """)
            db_size = self.cursor.fetchone()[0]
            
            # Number of tables
            self.cursor.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            table_count = self.cursor.fetchone()[0]
            
            # Cache hit ratio
            self.cursor.execute("""
                SELECT 
                    sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) as ratio
                FROM pg_statio_user_tables
            """)
            cache_ratio = self.cursor.fetchone()[0] or 0
            
            print(f"=== STATISTICS FOR {self.connection.info.dbname} ===\n")
            print(f"• Total size: {db_size}")
            print(f"• Number of tables: {table_count}")
            print(f"• Cache hit ratio: {cache_ratio:.2%}")
            
            # Top 5 largest tables
            self.cursor.execute("""
                SELECT 
                    schemaname || '.' || tablename as table_name,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
                FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                LIMIT 5
            """)
            
            top_tables = self.cursor.fetchall()
            if top_tables:
                print("\n=== TOP 5 LARGEST TABLES ===")
                headers = ['Table', 'Size']
                print(tabulate(top_tables, headers=headers, tablefmt='grid'))
                
        except Exception as e:
            print(f"\n✗ Error: {e}")
    
    def change_database(self):
        """Change database"""
        self.clear_screen()
        print("=== CHANGE DATABASE ===\n")
        
        # Show available databases
        try:
            self.cursor.execute("""
                SELECT datname FROM pg_database 
                WHERE datistemplate = false
                ORDER BY datname
            """)
            databases = [db[0] for db in self.cursor.fetchall()]
            
            print("Available databases:")
            for i, db in enumerate(databases, 1):
                print(f"  {i}. {db}")
            
            print(f"\nCurrently connected to: {self.connection.info.dbname}")
            db_name = input("\nNew database: ")
            
            # Save current credentials
            host = self.connection.info.host or 'localhost'
            port = self.connection.info.port
            user = self.connection.info.user
            
            self.disconnect()
            password = getpass.getpass("Password: ")
            
            if self.connect(host=host, port=port, database=db_name, user=user, password=password):
                print(f"\n✓ Changed to {db_name}")
            else:
                # Try to reconnect to previous database
                self.connect(host=host, port=port, database=self.connection.info.dbname, 
                           user=user, password=password)
        except Exception as e:
            print(f"\n✗ Error: {e}")
    
    def draw_menu(self, options, selected_index, title):
        """Draw menu with arrow navigation"""
        self.clear_screen()
        
        # Header
        print(self.term.bold("="*60))
        print(self.term.bold(title.center(60)))
        print(self.term.bold("="*60))
        
        if self.connection:
            print(f"\n{self.term.green}● Connected to: {self.connection.info.dbname}{self.term.normal}")
        else:
            print(f"\n{self.term.red}● Not connected{self.term.normal}")
        
        print("\nUse ↑/↓ to navigate, ENTER to select, ESC to exit")
        print("─" * 60 + "\n")
        
        # Menu options
        for i, option in enumerate(options):
            if i == selected_index:
                print(f"  {self.term.black_on_white} ▶ {option} {self.term.normal}")
            else:
                print(f"     {option}")
    
    def navigate_menu(self, options, title):
        """Navigate menu with keyboard"""
        selected_index = 0
        
        with self.term.cbreak(), self.term.hidden_cursor():
            while True:
                self.draw_menu(options, selected_index, title)
                
                key = self.term.inkey()
                
                if key.code == self.term.KEY_UP:
                    selected_index = (selected_index - 1) % len(options)
                elif key.code == self.term.KEY_DOWN:
                    selected_index = (selected_index + 1) % len(options)
                elif key.code == self.term.KEY_ENTER:
                    return selected_index
                elif key.code == self.term.KEY_ESCAPE:
                    return -1
    
    def wait_for_key(self):
        """Wait for user to press a key"""
        print(f"\nPress any key to continue...")
        with self.term.cbreak():
            self.term.inkey()
    
    def main_menu(self):
        """Main control panel menu"""
        options = [
            "Show databases",
            "Show tables",
            "Show active connections", 
            "Execute SQL query",
            "View table structure",
            "Database statistics",
            "Create backup",
            "Change database",
            "Exit"
        ]
        
        actions = {
            0: self.show_databases,
            1: self.show_tables,
            2: self.show_active_connections,
            3: self.execute_query,
            4: self.show_table_structure,
            5: self.show_statistics,
            6: self.backup_database,
            7: self.change_database
        }
        
        while True:
            choice = self.navigate_menu(options, "POSTGRESQL CONTROL PANEL")
            
            if choice == -1 or choice == 8:  # ESC or Exit
                break
            elif choice in actions:
                self.clear_screen()
                actions[choice]()
                self.wait_for_key()

def main():
    term = Terminal()
    panel = PostgreSQLControlPanel()
    
    print(term.clear())
    print(term.bold("=== POSTGRESQL CONTROL PANEL ===\n"))
    
    # Request connection parameters
    host = input("Host (default: localhost): ") or 'localhost'
    port = input("Port (default: 5432): ") or '5432'
    database = input("Initial database (default: postgres): ") or 'postgres'
    
    if panel.connect(host=host, port=int(port), database=database):
        try:
            panel.main_menu()
        except KeyboardInterrupt:
            print("\n\n✓ Exiting...")
        finally:
            panel.disconnect()
    
    print(term.clear())

if __name__ == "__main__":
    main()
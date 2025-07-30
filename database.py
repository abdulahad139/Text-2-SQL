import pymysql
import pandas as pd
from dotenv import load_dotenv
import os
from typing import Union, Dict, List, Optional

# Load environment variables
load_dotenv()

class DatabaseManager:
    def __init__(self, db_name: Optional[str] = None):
        self.connection = pymysql.connect(
            host=os.getenv('MYSQL_HOST'),
            user=os.getenv('MYSQL_USER'),
            password=os.getenv('MYSQL_PASSWORD'),
            database=db_name if db_name else os.getenv('MYSQL_DATABASE'),
            cursorclass=pymysql.cursors.DictCursor
        )
        self.current_db = db_name

    def get_available_databases(self):
        """List all available databases except system dbs"""
        with self.connection.cursor() as cursor:
            cursor.execute("SHOW DATABASES")
            return [db['Database'] for db in cursor.fetchall() 
                   if db['Database'] not in ('sys', 'information_schema', 'mysql', 'performance_schema')]

    def get_schema_info(self) -> str:
        """Extract schema information for LLM prompts"""
        if not self.current_db:
            raise ValueError("No database selected")
            
        schema = {"database": self.current_db, "tables": {}}
        with self.connection.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            tables = [table[f"Tables_in_{self.current_db}"] for table in cursor.fetchall()]
            
            for table in tables:
                cursor.execute(f"SHOW CREATE TABLE {table}")
                schema["tables"][table] = {
                    "structure": cursor.fetchone()['Create Table'],
                    "sample": self._get_sample_data(cursor, table)
                }
        
        return str(schema)

    def _get_sample_data(self, cursor, table: str, limit: int = 3) -> List[dict]:
        """Get sample table data"""
        cursor.execute(f"SELECT * FROM {table} LIMIT {limit}")
        return cursor.fetchall()

    def execute_query(self, query: str, params: tuple = None) -> Union[pd.DataFrame, None]:
        """Safe query execution with pandas DataFrame return"""
        try:
            # Basic query type filtering
            dangerous_keywords = ['DROP', 'TRUNCATE', 'ALTER', 'DELETE']
            query_type = query.strip().split()[0].upper()

            if any(danger in query.upper() for danger in dangerous_keywords):
                raise ValueError(f"Blocked dangerous query type: '{query_type}'")

            with self.connection.cursor() as cursor:
                cursor.execute(query, params or ())
                
                if query_type == 'SELECT':
                    return pd.DataFrame(cursor.fetchall())
                self.connection.commit()
                return None
                
        except Exception as e:
            self.connection.rollback()
            raise ValueError(f"Query execution failed: {str(e)}")

    def close(self):
        """Clean up connections"""
        if hasattr(self, 'connection') and self.connection:
            self.connection.close()

# Global instance (initially without specific database)
db_manager = DatabaseManager()

# Helper functions for backward compatibility
def get_schema_info():
    return db_manager.get_schema_info()

def execute_query(query: str, params: tuple = None):
    return db_manager.execute_query(query, params)
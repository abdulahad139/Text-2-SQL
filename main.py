from flask import Flask, request, jsonify, render_template, send_file
from database import DatabaseManager
from LLM.groq_client import GroqClient
import pymysql
import tempfile
import os

app = Flask(__name__)

# Initialize components
db_manager = DatabaseManager()
groq_client = GroqClient()

@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')

@app.route('/query', methods=['POST'])
def process_query():
    """Process natural language query and return SQL + results"""
    try:
        data = request.get_json()
        natural_query = data.get('query', '')
        
        if not natural_query:
            return jsonify({
                'status': 'error',
                'message': 'No query provided'
            })
        
        # Get database schema
        schema_info = db_manager.get_schema_info()
        
        # Generate SQL using Groq LLM
        generated_sql = groq_client.generate_sql(natural_query, schema_info)
        
        # Execute the generated SQL
        result_df = db_manager.execute_query(generated_sql)
        
        if result_df is not None:
            # Convert DataFrame to JSON-serializable format
            result_data = result_df.to_dict('records')
            
            return jsonify({
                'status': 'success',
                'query': generated_sql,
                'message': result_data,
                'row_count': len(result_data)
            })
        else:
            return jsonify({
                'status': 'success',
                'query': generated_sql,
                'message': 'Query executed successfully (no data returned)',
                'row_count': 0
            })
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'query': generated_sql if 'generated_sql' in locals() else None
        })



@app.route('/get-databases', methods=['GET'])
def get_databases():
    try:
        databases = db_manager.get_available_databases()
        return jsonify({'databases': databases})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/set-database', methods=['POST'])
def set_database():
    data = request.get_json()
    db_name = data.get('database')
    if not db_name:
        return jsonify({'error': 'Database name required'}), 400
    
    try:
        global db_manager
        db_manager.close()
        db_manager = DatabaseManager(db_name)
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download-excel', methods=['POST'])
def download_excel():
    """Download query results as Excel file"""
    try:
        data = request.get_json()
        sql_query = data.get('query', '')
        
        if not sql_query:
            return jsonify({
                'status': 'error',
                'message': 'No SQL query provided'
            }), 400
        
        # Execute query and get results
        result_df = db_manager.execute_query(sql_query)
        
        if result_df is None or result_df.empty:
            return jsonify({
                'status': 'error',
                'message': 'No data to export'
            }), 400
            
        # Create temp file
        temp_dir = tempfile.mkdtemp()
        filename = os.path.join(temp_dir, 'query_results.xlsx')
        result_df.to_excel(filename, index=False, engine='openpyxl')
        
        # Send file and schedule cleanup
        response = send_file(
            filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='query_results.xlsx'
        )
        
        # Clean up after sending
        @response.call_on_close
        def cleanup():
            try:
                os.remove(filename)
                os.rmdir(temp_dir)
            except Exception as e:
                app.logger.error(f"Error cleaning up temp file: {str(e)}")
        
        return response
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
if __name__ == '__main__':
    app.run(debug=True)
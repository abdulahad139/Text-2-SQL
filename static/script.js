document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const queryInput = document.getElementById('queryInput');
    const submitBtn = document.getElementById('submitQuery');
    const sqlOutput = document.getElementById('sqlOutput');
    const dataOutput = document.getElementById('dataOutput');
    const downloadBtn = document.getElementById('downloadExcel');
    const dbSelect = document.getElementById('database-select');
    const currentDbIndicator = document.getElementById('current-db');
    
    // Loader element
    const loader = document.createElement('div');
    loader.className = 'loader';
    dataOutput.parentNode.insertBefore(loader, dataOutput);

    // State
    let currentDatabase = null;

    // Initialize
    loadDatabases();

    // Event Listeners
    dbSelect.addEventListener('change', handleDatabaseChange);
    submitBtn.addEventListener('click', handleQuerySubmit);
    downloadBtn.addEventListener('click', downloadExcel);

    // Functions
    async function loadDatabases() {
        try {
            const response = await fetch('/get-databases');
            const data = await response.json();
            
            dbSelect.innerHTML = '';
            if (data.databases && data.databases.length > 0) {
                // Add database options
                data.databases.forEach(db => {
                    const option = document.createElement('option');
                    option.value = db;
                    option.textContent = db;
                    dbSelect.appendChild(option);
                });
                
                // Auto-select first database if only one exists
                if (data.databases.length === 1) {
                    dbSelect.value = data.databases[0];
                    await handleDatabaseChange({ target: dbSelect });
                }
            } else {
                dbSelect.innerHTML = '<option value="" disabled>No databases found</option>';
            }
        } catch (error) {
            console.error('Failed to load databases:', error);
            dbSelect.innerHTML = '<option value="" disabled>Error loading databases</option>';
        }
    }

    async function handleDatabaseChange(event) {
        const selectedDb = event.target.value;
        if (!selectedDb) return;

        try {
            const response = await fetch('/set-database', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ database: selectedDb })
            });

            if (!response.ok) throw new Error('Database switch failed');
            
            currentDatabase = selectedDb;
            currentDbIndicator.innerHTML = `<i class="fas fa-check-circle"></i> ${selectedDb}`;
            currentDbIndicator.style.color = '#28a745';
        } catch (error) {
            console.error('Database error:', error);
            currentDbIndicator.innerHTML = `<i class="fas fa-exclamation-circle"></i> Connection failed`;
            currentDbIndicator.style.color = '#dc3545';
            dbSelect.value = '';
        }
    }

    async function handleQuerySubmit() {
        const query = queryInput.value.trim();
        
        // Validate input
        if (!query) {
            showError('Please enter a query');
            return;
        }
        if (!currentDatabase) {
            showError('Please select a database first');
            return;
        }

        // UI State
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
        loader.style.display = 'block';
        dataOutput.innerHTML = '';

        try {
            const response = await fetch('/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query })
            });

            const result = await response.json();
            
            if (result.status === 'success') {
                // Display SQL
                sqlOutput.innerHTML = `<pre><code>${result.query}</code></pre>`;
                
                // Display results
                if (result.row_count > 0) {
                    dataOutput.innerHTML = createTableHTML(result.message);
                } else {
                    dataOutput.innerHTML = '<div class="alert alert-info">No data returned from query</div>';
                }
                
                downloadBtn.disabled = false;
            } else {
                showError(result.message, result.query);
            }
        } catch (error) {
            showError(error.message);
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fas fa-play"></i> Generate SQL & Execute';
            loader.style.display = 'none';
        }
    }

    function createTableHTML(data) {
        if (!data || data.length === 0) return '';
        
        const headers = Object.keys(data[0]);
        let html = '<table><thead><tr>';
        
        // Create headers
        headers.forEach(header => {
            html += `<th>${header}</th>`;
        });
        html += '</tr></thead><tbody>';
        
        // Create rows
        data.forEach(row => {
            html += '<tr>';
            headers.forEach(header => {
                html += `<td>${row[header] !== null ? row[header] : 'NULL'}</td>`;
            });
            html += '</tr>';
        });
        
        return html + '</tbody></table>';
    }

    function showError(message, sql = null) {
        let errorHTML = `
            <div class="alert alert-error">
                <i class="fas fa-exclamation-triangle"></i> ${message}
        `;
        
        if (sql) {
            errorHTML += `
                <details class="error-details">
                    <summary>Technical Details</summary>
                    <pre>${sql}</pre>
                </details>
            `;
        }
        
        errorHTML += '</div>';
        dataOutput.innerHTML = errorHTML;
    }

    async function downloadExcel() {
        const sqlQuery = sqlOutput.textContent;
        if (!sqlQuery || sqlQuery.includes("SQL query will appear here")) {
            alert('Please generate a query first');
            return;
        }

        try {
            downloadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Preparing...';
            downloadBtn.disabled = true;
            
            const response = await fetch('/download-excel', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: sqlQuery })
            });

            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `results_${new Date().toISOString().slice(0,10)}.xlsx`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
            } else {
                const error = await response.json();
                throw new Error(error.message || 'Download failed');
            }
        } catch (error) {
            showError(`Excel download failed: ${error.message}`);
        } finally {
            downloadBtn.innerHTML = '<i class="fas fa-file-excel"></i> Download as Excel';
            downloadBtn.disabled = false;
        }
    }
});
#!/bin/bash
# Export PostgreSQL tables to HTML report

# Load config
if [ -f ".env" ]; then
    source .env
fi

OUTPUT_FILE="postgresql_report_$(date +%Y%m%d_%H%M%S).html"

cat > "$OUTPUT_FILE" << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>PostgreSQL Database Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
        tr:nth-child(even) { background-color: #f2f2f2; }
        h2 { color: #333; margin-top: 30px; }
        .info { background-color: #e8f5e9; padding: 10px; margin: 10px 0; }
    </style>
</head>
<body>
    <h1>PostgreSQL Database Report</h1>
    <div class="info">
EOF

echo "Generated: $(date)" >> "$OUTPUT_FILE"
echo "<br>Database: ${AUTOTRAINX_DB_NAME:-autotrainx}" >> "$OUTPUT_FILE"
echo "<br>Host: ${AUTOTRAINX_DB_HOST:-localhost}" >> "$OUTPUT_FILE"
echo "</div>" >> "$OUTPUT_FILE"

# Get list of tables
TABLES=$(PGPASSWORD="${AUTOTRAINX_DB_PASSWORD:-1234}" psql -h "${AUTOTRAINX_DB_HOST:-localhost}" \
    -U "${AUTOTRAINX_DB_USER:-autotrainx}" -d "${AUTOTRAINX_DB_NAME:-autotrainx}" \
    -t -c "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;")

# Export each table
for TABLE in $TABLES; do
    echo "<h2>Table: $TABLE</h2>" >> "$OUTPUT_FILE"
    
    # Get row count
    COUNT=$(PGPASSWORD="${AUTOTRAINX_DB_PASSWORD:-1234}" psql -h "${AUTOTRAINX_DB_HOST:-localhost}" \
        -U "${AUTOTRAINX_DB_USER:-autotrainx}" -d "${AUTOTRAINX_DB_NAME:-autotrainx}" \
        -t -c "SELECT COUNT(*) FROM $TABLE;")
    
    echo "<p>Total rows: $COUNT</p>" >> "$OUTPUT_FILE"
    
    # Export table as HTML
    PGPASSWORD="${AUTOTRAINX_DB_PASSWORD:-1234}" psql -h "${AUTOTRAINX_DB_HOST:-localhost}" \
        -U "${AUTOTRAINX_DB_USER:-autotrainx}" -d "${AUTOTRAINX_DB_NAME:-autotrainx}" \
        -H -c "SELECT * FROM $TABLE LIMIT 100;" >> "$OUTPUT_FILE"
done

echo "</body></html>" >> "$OUTPUT_FILE"

echo "Report generated: $OUTPUT_FILE"
echo "You can download this file and open it in a browser"
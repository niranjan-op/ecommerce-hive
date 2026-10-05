#!/usr/bin/env bash
# =============================================================================
# run_pipeline.sh
# Full end-to-end pipeline script.
#
# Adjust variables at the top to match your installation.
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# CONFIGURATION — edit these to match your environment
# ---------------------------------------------------------------------------
HIVE_BIN="${HIVE_HOME:-/usr/local/hive}/bin/hive"
HDFS_BIN="${HADOOP_HOME:-/usr/local/hadoop}/bin/hdfs"
PYTHON_BIN="${PYTHON_BIN:-python3}"

HDFS_BASE="/user/hive/warehouse/ecommerce/staging"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="$PROJECT_DIR/data"

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
log() { echo -e "\n\033[1;34m==>\033[0m $*"; }
err() { echo -e "\n\033[1;31m✗  ERROR:\033[0m $*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# 0. Pre-flight checks
# ---------------------------------------------------------------------------
log "Step 0 — Pre-flight checks"

command -v "$PYTHON_BIN" >/dev/null 2>&1 || \
    err "Python not found at '$PYTHON_BIN'. Set PYTHON_BIN env var."

command -v "$HDFS_BIN" >/dev/null 2>&1 || \
    err "HDFS binary not found at '$HDFS_BIN'. Set HADOOP_HOME env var."

command -v "$HIVE_BIN" >/dev/null 2>&1 || \
    err "Hive binary not found at '$HIVE_BIN'. Set HIVE_HOME env var."

# Check HDFS is up by listing root
"$HDFS_BIN" dfs -ls / >/dev/null 2>&1 || \
    err "HDFS is not reachable. Run:  start-all.sh"

echo "All pre-flight checks passed."

# ---------------------------------------------------------------------------
# 1. Generate synthetic data
# ---------------------------------------------------------------------------
log "Step 1 — Generating synthetic data"
cd "$PROJECT_DIR"
"$PYTHON_BIN" data_generator/generate_data.py \
    --customers 10000 \
    --products  2000  \
    --orders    100000

ls -lh "$DATA_DIR"

# ---------------------------------------------------------------------------
# 2. Upload CSV files to HDFS
# ---------------------------------------------------------------------------
log "Step 2 — Uploading CSV files to HDFS"

for TABLE in customers products orders order_items payments; do
    HDFS_PATH="$HDFS_BASE/$TABLE"
    echo "  Uploading $TABLE.csv → hdfs://$HDFS_PATH/"

    # Remove previous version if it exists
    "$HDFS_BIN" dfs -rm -r -f "$HDFS_PATH" >/dev/null 2>&1 || true

    "$HDFS_BIN" dfs -mkdir -p "$HDFS_PATH"
    "$HDFS_BIN" dfs -put "$DATA_DIR/${TABLE}.csv" "$HDFS_PATH/"
done

echo "HDFS listing:"
"$HDFS_BIN" dfs -ls "$HDFS_BASE"

# ---------------------------------------------------------------------------
# 3. Create Hive database and tables
# ---------------------------------------------------------------------------
log "Step 3 — Creating Hive database and tables"
"$HIVE_BIN" -f "$PROJECT_DIR/hive/01_create_database.sql"
"$HIVE_BIN" -f "$PROJECT_DIR/hive/02_create_tables.sql"

# ---------------------------------------------------------------------------
# 4. Load data from staging → ORC analytical tables
# ---------------------------------------------------------------------------
log "Step 4 — Loading data into ORC analytical tables"
"$HIVE_BIN" -f "$PROJECT_DIR/hive/03_load_data.sql"

# ---------------------------------------------------------------------------
# 5. Run data quality checks
# ---------------------------------------------------------------------------
log "Step 5 — Running data quality transforms / checks"
"$HIVE_BIN" -f "$PROJECT_DIR/hive/04_transform_data.sql"

# ---------------------------------------------------------------------------
# 6. Run a sample analytics query to verify
# ---------------------------------------------------------------------------
log "Step 6 — Sample analytics query (revenue by category)"
"$HIVE_BIN" -e "
USE ecommerce;
SELECT p.category,
       ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue
FROM fact_order_items oi
JOIN dim_products p ON oi.product_id = p.product_id
JOIN fact_orders  o ON oi.order_id   = o.order_id
WHERE o.order_status = 'Delivered'
GROUP BY p.category
ORDER BY revenue DESC;
"

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
log "Pipeline complete!"
echo ""
echo "Next steps:"
echo "  1. Start the dashboard:  cd $PROJECT_DIR && streamlit run dashboard/app.py"
echo "  2. Or run benchmarks:    $PYTHON_BIN benchmark/benchmark.py"
echo ""

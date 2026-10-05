# =============================================================================
# run_pipeline.ps1
# PowerShell-native pipeline runner for the ecommerce-hive project.
#
# Run from the BDA Project\ directory (where your venv lives):
#   .\ecommerce-hive\scripts\run_pipeline.ps1
#
# Or from within ecommerce-hive\:
#   .\scripts\run_pipeline.ps1
# =============================================================================

$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Resolve project root regardless of where the script is called from
# ---------------------------------------------------------------------------
$SCRIPT_DIR  = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_DIR = Split-Path -Parent $SCRIPT_DIR   # ecommerce-hive\
$DATA_DIR    = Join-Path $PROJECT_DIR "data"

Write-Host ""
Write-Host "=== E-Commerce Hive Pipeline ===" -ForegroundColor Cyan
Write-Host "Project : $PROJECT_DIR"
Write-Host "Data    : $DATA_DIR"
Write-Host ""

# ---------------------------------------------------------------------------
# Helper: print step header
# ---------------------------------------------------------------------------
function Step($n, $msg) {
    Write-Host ""
    Write-Host "--- Step $n : $msg ---" -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# Helper: check if a command exists
# ---------------------------------------------------------------------------
function Has-Command($cmd) {
    $null -ne (Get-Command $cmd -ErrorAction SilentlyContinue)
}

# ===========================================================================
# STEP 1 — Generate synthetic data
# ===========================================================================
Step 1 "Generate synthetic data"

$gen_script = Join-Path $PROJECT_DIR "data_generator\generate_data.py"
python $gen_script --customers 10000 --products 2000 --orders 100000

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Data generation failed." -ForegroundColor Red
    exit 1
}
Write-Host "Data generation complete." -ForegroundColor Green

# ===========================================================================
# STEP 2 — Upload CSVs to HDFS
# ===========================================================================
Step 2 "Upload CSV files to HDFS"

if (-not (Has-Command "hdfs")) {
    Write-Host "SKIP: 'hdfs' command not found." -ForegroundColor Magenta
    Write-Host "  Install Hadoop and add it to PATH, then re-run." -ForegroundColor Magenta
    Write-Host "  See README.md Section 13 for installation steps." -ForegroundColor Magenta
} else {
    $tables = @("customers", "products", "orders", "order_items", "payments")
    foreach ($t in $tables) {
        $hdfs_path = "/user/hive/warehouse/ecommerce/staging/$t"
        Write-Host "  Uploading $t.csv -> hdfs://$hdfs_path/"
        hdfs dfs -mkdir -p $hdfs_path
        hdfs dfs -put -f "$DATA_DIR\$t.csv" "$hdfs_path/"
    }
    Write-Host "HDFS upload complete." -ForegroundColor Green
}

# ===========================================================================
# STEP 3 — Create Hive database
# ===========================================================================
Step 3 "Create Hive database"

if (-not (Has-Command "hive")) {
    Write-Host "SKIP: 'hive' command not found." -ForegroundColor Magenta
    Write-Host "  Install Apache Hive and add it to PATH, then re-run." -ForegroundColor Magenta
} else {
    hive -f "$PROJECT_DIR\hive\01_create_database.sql"
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR in Step 3" -ForegroundColor Red; exit 1 }
    Write-Host "Database created." -ForegroundColor Green
}

# ===========================================================================
# STEP 4 — Create Hive tables
# ===========================================================================
Step 4 "Create Hive staging and analytical tables"

if (Has-Command "hive") {
    hive -f "$PROJECT_DIR\hive\02_create_tables.sql"
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR in Step 4" -ForegroundColor Red; exit 1 }
    Write-Host "Tables created." -ForegroundColor Green
} else {
    Write-Host "SKIP: Hive not available." -ForegroundColor Magenta
}

# ===========================================================================
# STEP 5 — Load data into ORC analytical tables
# ===========================================================================
Step 5 "Load CSV staging -> ORC analytical tables"

if (Has-Command "hive") {
    hive -f "$PROJECT_DIR\hive\03_load_data.sql"
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR in Step 5" -ForegroundColor Red; exit 1 }
    Write-Host "ORC tables loaded." -ForegroundColor Green
} else {
    Write-Host "SKIP: Hive not available." -ForegroundColor Magenta
}

# ===========================================================================
# STEP 6 — Data quality checks
# ===========================================================================
Step 6 "Data quality transforms and checks"

if (Has-Command "hive") {
    hive -f "$PROJECT_DIR\hive\04_transform_data.sql"
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR in Step 6" -ForegroundColor Red; exit 1 }
    Write-Host "Quality checks passed." -ForegroundColor Green
} else {
    Write-Host "SKIP: Hive not available." -ForegroundColor Magenta
}

# ===========================================================================
# Done
# ===========================================================================
Write-Host ""
Write-Host "=== Pipeline finished ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor White
Write-Host "  Start the Streamlit dashboard:"
Write-Host "    cd `"$PROJECT_DIR`""
Write-Host "    streamlit run dashboard\app.py"
Write-Host ""
Write-Host "  Run benchmarks:"
Write-Host "    python `"$PROJECT_DIR\benchmark\benchmark.py`""
Write-Host ""

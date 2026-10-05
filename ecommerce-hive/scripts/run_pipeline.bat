@echo off
REM ============================================================================
REM run_pipeline.bat
REM Windows-compatible pipeline runner.
REM Run from within the ecommerce-hive\ directory.
REM ============================================================================

SET PROJECT_DIR=%~dp0..
SET DATA_DIR=%PROJECT_DIR%\data
SET PYTHON_BIN=python

echo.
echo === Step 1: Generate synthetic data ===
%PYTHON_BIN% "%PROJECT_DIR%\data_generator\generate_data.py" ^
    --customers 10000 --products 2000 --orders 100000
IF ERRORLEVEL 1 (
    echo ERROR: Data generation failed.
    exit /b 1
)

echo.
echo === Step 2: Upload CSVs to HDFS ===
echo NOTE: Make sure HDFS is running (start-all.cmd or start-dfs.cmd)
hdfs dfs -mkdir -p /user/hive/warehouse/ecommerce/staging/customers
hdfs dfs -mkdir -p /user/hive/warehouse/ecommerce/staging/products
hdfs dfs -mkdir -p /user/hive/warehouse/ecommerce/staging/orders
hdfs dfs -mkdir -p /user/hive/warehouse/ecommerce/staging/order_items
hdfs dfs -mkdir -p /user/hive/warehouse/ecommerce/staging/payments

hdfs dfs -put -f "%DATA_DIR%\customers.csv"   /user/hive/warehouse/ecommerce/staging/customers/
hdfs dfs -put -f "%DATA_DIR%\products.csv"    /user/hive/warehouse/ecommerce/staging/products/
hdfs dfs -put -f "%DATA_DIR%\orders.csv"      /user/hive/warehouse/ecommerce/staging/orders/
hdfs dfs -put -f "%DATA_DIR%\order_items.csv" /user/hive/warehouse/ecommerce/staging/order_items/
hdfs dfs -put -f "%DATA_DIR%\payments.csv"    /user/hive/warehouse/ecommerce/staging/payments/

echo.
echo === Step 3: Create Hive database and tables ===
hive -f "%PROJECT_DIR%\hive\01_create_database.sql"
hive -f "%PROJECT_DIR%\hive\02_create_tables.sql"

echo.
echo === Step 4: Load ORC tables ===
hive -f "%PROJECT_DIR%\hive\03_load_data.sql"

echo.
echo === Step 5: Data quality checks ===
hive -f "%PROJECT_DIR%\hive\04_transform_data.sql"

echo.
echo === Pipeline complete! ===
echo Start the dashboard:
echo     streamlit run "%PROJECT_DIR%\dashboard\app.py"
echo.

#!/bin/bash

echo "Starting Bengaluru Traffic Intelligence Dashboard..."

# Check if processed data exists
if [ ! -f "data/processed/violations_clean.parquet" ]; then
    echo "Running data pipeline for first-time setup..."
    python run_pipeline.py
else
    echo "Using existing processed data..."
fi

# Start Streamlit
streamlit run app/dashboard.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true --server.enableCORS=false --server.enableXsrfProtection=false

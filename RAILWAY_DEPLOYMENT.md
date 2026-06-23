# Railway Deployment Guide

## Prerequisites

1. **Railway Account**: Sign up at [railway.app](https://railway.app)
2. **GitHub Repository**: Your code is already pushed to GitHub
3. **CSV Data File**: Upload your violation data to Railway

## Deployment Steps

### 1. Create New Railway Project

1. Go to [railway.app](https://railway.app)
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Connect your GitHub account if not already connected
5. Select the repository: `Madukalmanoj/-Bengaluru_Parking_Congestion_Intelligence`

### 2. Configure Environment Variables

In Railway dashboard, go to your project → Variables tab and add:

```
CSV_PATH=/app/data/raw/violations.csv
PORT=8080
```

### 3. Upload Your Data File

You have two options:

#### Option A: Using Railway Volume (Recommended)
1. In Railway dashboard, go to your service
2. Click "Volumes" tab
3. Create a new volume mounted at `/app/data/raw`
4. Upload your CSV file via Railway CLI or dashboard

#### Option B: Store in GitHub (if file is small)
1. Copy your CSV file to `data/raw/violations.csv`
2. Update `.gitignore` to allow this file
3. Commit and push to GitHub

### 4. Build and Deploy

Railway will automatically:
- Detect it's a Python project
- Install dependencies from `requirements.txt`
- Run the startup script
- Process data on first run
- Start the Streamlit dashboard

### 5. Access Your App

Once deployed, Railway will provide a URL like:
```
https://your-project.up.railway.app
```

## Post-Deployment

### Check Logs
Monitor deployment in Railway dashboard → Deployments tab → View logs

### Common Issues

**Issue**: "CSV file not found"
- **Solution**: Ensure CSV_PATH environment variable points to correct location
- Check if file was uploaded successfully

**Issue**: "Out of memory during processing"
- **Solution**: Upgrade Railway plan for more memory
- Or preprocess data locally and upload processed `.parquet` files

**Issue**: "Port binding error"
- **Solution**: Ensure PORT environment variable is set (Railway auto-sets this)

## Pre-processing Data Locally (Optional)

To reduce Railway build time, you can preprocess data locally:

```bash
# Run locally
python run_pipeline.py

# This creates processed files in data/processed/
# Upload these files to Railway instead of raw CSV
```

## File Structure for Railway

```
.
├── app/
│   └── dashboard.py          # Main Streamlit app
├── src/                      # Processing modules
├── data/
│   ├── raw/
│   │   └── violations.csv    # Upload your CSV here
│   └── processed/            # Auto-generated
├── config.py                 # Configuration (env-aware)
├── requirements.txt          # Python dependencies
├── runtime.txt              # Python version
├── Procfile                 # Railway process definition
├── railway.toml             # Railway configuration
├── start.sh                 # Startup script
└── .streamlit/
    └── config.toml          # Streamlit settings
```

## Railway-Specific Optimizations

1. **Persistent Storage**: Use Railway Volumes for data that needs to persist
2. **Environment Variables**: Store sensitive config in Railway Variables
3. **Memory Management**: Monitor usage and upgrade plan if needed
4. **Auto-scaling**: Railway handles this automatically
5. **HTTPS**: Automatically provided by Railway

## Estimated Railway Costs

- **Starter Plan**: $5/month (512MB RAM) - Good for small datasets
- **Developer Plan**: $10/month (2GB RAM) - Recommended for full dataset
- **Team Plan**: $20/month (4GB RAM) - For production use

## Support

For Railway-specific issues:
- [Railway Docs](https://docs.railway.app)
- [Railway Discord](https://discord.gg/railway)

For project-specific issues:
- Check the main README.md
- Review application logs in Railway dashboard

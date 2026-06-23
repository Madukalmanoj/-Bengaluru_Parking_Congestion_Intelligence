# Streamlit Cloud Deployment Guide

## 🚀 Quick Deploy (2 Minutes)

### Prerequisites
- GitHub repository with your code (✅ Already done!)
- Streamlit Cloud account (free)

### Step 1: Sign Up for Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click **"Sign up with GitHub"**
3. Authorize Streamlit to access your GitHub account

### Step 2: Deploy Your App

1. Click **"New app"** button
2. Fill in the deployment form:
   - **Repository**: `Madukalmanoj/-Bengaluru_Parking_Congestion_Intelligence`
   - **Branch**: `main`
   - **Main file path**: `app/dashboard.py`
3. Click **"Deploy!"**

That's it! Streamlit will automatically:
- Detect Python dependencies from `requirements.txt`
- Install system packages from `packages.txt`
- Run the data pipeline on first load
- Launch your dashboard

### Step 3: Configure Secrets (Optional)

If you need to upload your CSV file:

1. In Streamlit Cloud dashboard, click your app
2. Go to **Settings** → **Secrets**
3. Add any API keys or configuration (if needed)

Alternatively, you can:
- Use the GitHub repository to store processed `.parquet` files
- Upload data directly to the app (smaller datasets)

## 📁 Required Files for Streamlit Cloud

Your repository already has these files configured:

### ✅ `requirements.txt`
Python dependencies - Streamlit Cloud automatically installs these

### ✅ `packages.txt`
System-level packages needed for OSM and geospatial libraries

### ✅ `.streamlit/config.toml`
Streamlit configuration (theme, server settings)

### ✅ `app/dashboard.py`
Your main Streamlit application

## 🎯 App URL

Once deployed, your app will be available at:
```
https://[your-app-name].streamlit.app
```

Example: `https://bengaluru-traffic-intelligence.streamlit.app`

## 🔧 Post-Deployment

### Monitor Your App
- View logs in real-time from Streamlit Cloud dashboard
- See resource usage (CPU, memory)
- Check deployment status

### Update Your App
Any push to the `main` branch automatically triggers a redeploy!

```bash
git add .
git commit -m "Update dashboard"
git push origin main
```

Streamlit Cloud will rebuild and redeploy automatically.

### Common Issues & Solutions

#### Issue: "Module not found"
**Solution**: Add missing package to `requirements.txt`

#### Issue: "System library not found"
**Solution**: Add required system package to `packages.txt`

#### Issue: "CSV file not found"
**Solution**: 
- Option A: Upload preprocessed `.parquet` files to GitHub
- Option B: Add file upload widget in the app
- Option C: Use Streamlit secrets for cloud storage URLs

#### Issue: "App timeout during startup"
**Solution**: Preprocess data locally and upload `.parquet` files:
```bash
# Run locally
python run_pipeline.py

# Commit processed files (update .gitignore first)
git add data/processed/*.parquet
git commit -m "Add preprocessed data"
git push
```

## 💾 Data Handling Options

### Option 1: Preprocess Locally (Recommended)
```bash
# Process data locally
python run_pipeline.py

# Update .gitignore to allow .parquet files
# Remove these lines from .gitignore:
# data/processed/*.parquet

# Commit processed data
git add data/processed/*.parquet
git commit -m "Add preprocessed data"
git push origin main
```

### Option 2: Use Streamlit File Uploader
Add to your dashboard:
```python
uploaded_file = st.file_uploader("Upload violations CSV", type="csv")
if uploaded_file:
    df = pd.read_csv(uploaded_file)
```

### Option 3: Cloud Storage Integration
Store data in:
- Google Drive
- AWS S3
- Google Cloud Storage
- Dropbox

Access via URLs or APIs with credentials in Streamlit Secrets.

## 📊 Resource Limits (Free Tier)

- **CPU**: 1 vCPU
- **Memory**: 1 GB RAM
- **Storage**: Limited (use for code, not large datasets)
- **Apps**: Unlimited public apps
- **Runtime**: Apps sleep after 7 days of inactivity

**Tip**: For large datasets (100MB+), preprocess locally and upload `.parquet` files.

## 🎨 Customization

### Update Theme
Edit `.streamlit/config.toml`:
```toml
[theme]
primaryColor = "#fc8d59"     # Your brand color
backgroundColor = "#0e1117"   # Dark mode
textColor = "#fafafa"        # Light text
```

### Custom Domain (Paid Plans)
Streamlit Team/Enterprise plans allow custom domains.

## 🔒 Security

### Public vs Private Apps
- **Free**: Apps are public (anyone with URL can access)
- **Paid**: Private apps with authentication

### Protect Sensitive Data
- Don't commit API keys or passwords
- Use Streamlit Secrets for credentials
- Use environment variables for configuration

## 💰 Pricing

| Plan | Price | Features |
|------|-------|----------|
| **Community** | Free | Unlimited public apps, 1GB RAM |
| **Team** | $250/mo | Private apps, SSO, 4GB RAM |
| **Enterprise** | Custom | Custom domains, dedicated support |

**For your hackathon**: Free Community tier is perfect!

## 📱 Sharing Your App

Once deployed, share the URL:
```
https://[your-app-name].streamlit.app
```

Features:
- ✅ Responsive design (works on mobile)
- ✅ HTTPS enabled by default
- ✅ Fast global CDN
- ✅ Automatic SSL certificates

## 🆘 Support & Resources

- [Streamlit Docs](https://docs.streamlit.io)
- [Community Forum](https://discuss.streamlit.io)
- [Deployment Guide](https://docs.streamlit.io/streamlit-community-cloud)
- [Example Apps](https://streamlit.io/gallery)

## 📋 Pre-Deployment Checklist

- [x] Code pushed to GitHub
- [x] `requirements.txt` with all dependencies
- [x] `packages.txt` for system packages
- [x] `.streamlit/config.toml` for configuration
- [x] Main file at `app/dashboard.py`
- [ ] Sign up for Streamlit Cloud
- [ ] Deploy app
- [ ] Test deployed app
- [ ] Share URL with stakeholders

## 🎉 You're Ready to Deploy!

Just go to [share.streamlit.io](https://share.streamlit.io) and click "New app"!

Your app structure is already optimized for Streamlit Cloud. All configuration files are in place. Just point Streamlit to your GitHub repo and you're live in 2 minutes! 🚀

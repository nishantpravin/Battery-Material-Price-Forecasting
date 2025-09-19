# 🚀 Deployment Guide

This guide will help you deploy the Battery Cost Forecast app to Streamlit Cloud.

## 📋 Prerequisites

1. **GitHub Account**: You need a GitHub account to host your code
2. **Streamlit Cloud Account**: Sign up at [share.streamlit.io](https://share.streamlit.io)
3. **Code Repository**: Your code should be in a GitHub repository

## 🔧 Step 1: Prepare Your Repository

### 1.1 Initialize Git (if not already done)
```bash
git init
git add .
git commit -m "Initial commit: Battery Cost Forecast app"
```

### 1.2 Create GitHub Repository
1. Go to [GitHub](https://github.com) and create a new repository
2. Name it `battery-cost-forecast` (or your preferred name)
3. Make it public (required for free Streamlit Cloud)

### 1.3 Push to GitHub
```bash
git remote add origin https://github.com/YOUR_USERNAME/battery-cost-forecast.git
git branch -M main
git push -u origin main
```

## 🌐 Step 2: Deploy to Streamlit Cloud

### 2.1 Access Streamlit Cloud
1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with your GitHub account
3. Click "New App"

### 2.2 Configure Your App
1. **Repository**: Select your `battery-cost-forecast` repository
2. **Branch**: Select `main` (or your default branch)
3. **Main file path**: Enter `app/app.py`
4. **App URL**: Choose a custom URL (optional)

### 2.3 Set Environment Variables (Optional)
In the "Advanced settings" section, you can add:

```
ROLLING_MONTHS=60
FORECAST_MONTHS=120
RAPIDAPI_KEY=your_rapidapi_key_here
NICKEL_ID=959207
LITHIUM_ID=997886
COBALT_ID=944610
```

### 2.4 Deploy
Click "Deploy!" and wait for the deployment to complete.

## 🔐 Step 3: Configure Secrets (Optional)

If you want to use API keys or sensitive data:

1. In your Streamlit Cloud app dashboard
2. Go to "Settings" → "Secrets"
3. Add your secrets in TOML format:

```toml
RAPIDAPI_KEY = "your_actual_rapidapi_key"
NICKEL_ID = "959207"
LITHIUM_ID = "997886"
COBALT_ID = "944610"
```

## 📊 Step 4: Test Your Deployment

1. Visit your deployed app URL
2. Test the "API Mode" functionality
3. Test the "Physical Mode" file upload
4. Verify all features work correctly

## 🔄 Step 5: Updates and Maintenance

### Updating Your App
1. Make changes to your code locally
2. Commit and push to GitHub:
   ```bash
   git add .
   git commit -m "Update: Add new features"
   git push
   ```
3. Streamlit Cloud will automatically redeploy

### Monitoring
- Check the "Logs" tab in your Streamlit Cloud dashboard for any errors
- Monitor app performance and usage

## 🛠️ Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are in `requirements.txt`
2. **File Not Found**: Check file paths are relative to the app root
3. **API Errors**: Verify API keys are set correctly in secrets
4. **Memory Issues**: Consider upgrading to a paid Streamlit Cloud plan

### Getting Help
- Check Streamlit Cloud documentation
- Review app logs in the dashboard
- Test locally first before deploying

## 🎯 Production Tips

1. **Performance**: Use caching for expensive operations
2. **Security**: Never commit API keys to your repository
3. **Monitoring**: Set up alerts for app downtime
4. **Backup**: Keep local backups of your data

## 📈 Scaling

For high-traffic applications:
- Consider upgrading to Streamlit Cloud Pro
- Implement proper error handling
- Add data validation
- Use external databases for data storage

---

**Your app is now live! 🎉**

Share your deployed app URL with others to showcase your battery cost forecasting capabilities.

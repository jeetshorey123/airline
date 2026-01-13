# Airline Invoice PDF to Excel Converter

## Deploy to Render.com (Free, No Limits)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

### Quick Deploy Steps:

1. **Fork this repo** to your GitHub
2. **Go to [Render.com](https://render.com)** and sign up (free)
3. **Create New Web Service**
4. **Connect your GitHub repo**
5. **Configure:**
   - Name: `airline-pdf-converter`
   - Environment: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app --timeout 300 --workers 2`
   - Instance Type: **Free** (512MB RAM) or **Starter** (1GB RAM - $7/month)
6. **Click Create Web Service**

### Features:
- ✅ No timeout limits (process 1000s of files)
- ✅ 512MB - 1GB RAM available
- ✅ Always-on service (not serverless)
- ✅ Free SSL certificate
- ✅ Auto-deploy on git push

### Local Development:

```bash
pip install -r requirements.txt
python app.py
```

Visit `http://localhost:5000`

## Vercel NOT Recommended

Vercel has severe limitations for this use case:
- ❌ 10 second timeout (free tier)
- ❌ 50MB max deployment size
- ❌ Serverless architecture (not suitable for long processing)

Use Render.com or Railway.app instead for production.

# Deployment Guide - Air India PDF Extractor

## Fixed Issues ✅

1. **Updated Python runtime** from 3.9 to 3.11
2. **Fixed pandas version** - removed strict version lock that required compilation
3. **Added gunicorn** to api/requirements.txt
4. **Updated vercel.json** with proper configuration

---

## Best Deployment Options

### 🚀 Option 1: Railway.app (RECOMMENDED)
**Best for: Long processing times, large PDFs**

1. Go to [Railway.app](https://railway.app)
2. Sign in with GitHub
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your repository
5. Railway will automatically detect `railway.json` and deploy
6. **No additional configuration needed!**

**Why Railway:**
- ✅ No timeout limits (can process 1000s of PDFs)
- ✅ 512MB RAM (free tier) or upgradeable
- ✅ Automatic deployments on git push
- ✅ Free SSL certificate
- ✅ $5/month for 500 hours

---

### 🔧 Option 2: Render.com (RECOMMENDED)
**Best for: Reliable deployment, no timeout limits**

1. Go to [Render.com](https://render.com)
2. Sign up (free)
3. Click "New" → "Web Service"
4. Connect your GitHub repository
5. Configure:
   - **Name:** `airline-pdf-converter`
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app --timeout 300 --workers 2`
   - **Instance Type:** Free (512MB) or Starter ($7/month, 1GB)
6. Click "Create Web Service"

**Why Render:**
- ✅ Free tier with 512MB RAM
- ✅ No timeout limits
- ✅ Always-on service
- ✅ Auto-deploy on git push
- ✅ Free SSL certificate

---

### ⚠️ Option 3: Vercel (LIMITED - Use for testing only)
**Limitations:**
- ❌ 10-second timeout on free tier (60s on Pro)
- ❌ Can only process 1-2 PDFs at a time
- ❌ Serverless architecture = cold starts

**Deploy to Vercel:**
1. Install Vercel CLI: `npm install -g vercel`
2. Run: `vercel`
3. Follow the prompts

**Or use GitHub Integration:**
1. Go to [vercel.com](https://vercel.com)
2. Import your GitHub repository
3. Vercel will auto-detect `vercel.json`
4. Click Deploy

---

## Testing Deployment

After deploying, test with:

1. **Upload a small PDF** (1-2 pages) first
2. **Check the progress endpoint**: `https://your-app.com/progress`
3. **Upload multiple PDFs** to test batch processing

---

## Troubleshooting

### Error: "Package installation failed"
**Fix:** Make sure requirements.txt has proper versions:
```
Flask>=3.0.0
flask-cors>=4.0.0
pdfplumber>=0.10.3
pandas>=2.0.0
openpyxl>=3.1.2
Werkzeug>=3.0.1
gunicorn>=21.2.0
```

### Error: "Function timeout"
**Fix:** Use Railway or Render, not Vercel

### Error: "Module not found"
**Fix:** Ensure `api/requirements.txt` exists and has all dependencies

### Error: "No such file or directory: /tmp"
**Fix:** The code already handles this - uses `/tmp` for serverless, local folders otherwise

---

## Git Commands to Deploy

```bash
# Commit the changes
git add .
git commit -m "Fix deployment configuration"
git push origin main

# Your deployment platform will automatically redeploy
```

---

## Environment Variables (if needed)

Some platforms may need:
- `PYTHON_VERSION=3.11`
- `PORT=5000` (auto-set by most platforms)

---

## Quick Test Command

Test locally before deploying:
```bash
# Activate virtual environment
.venv-1\Scripts\Activate.ps1

# Install requirements
pip install -r requirements.txt

# Run app
python app.py

# Visit http://localhost:5000
```

---

## Support

If deployment still fails:
1. Check platform logs
2. Verify all requirements are installed
3. Ensure Python 3.11 is being used
4. Try Railway.app (most reliable for this app)

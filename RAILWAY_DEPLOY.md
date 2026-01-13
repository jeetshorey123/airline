# Deploy to Railway.app - 1 MINUTE SETUP

## Why Railway?
- ✅ **No file size limits** (upload GBs of PDFs)
- ✅ **No timeout limits** (process for hours if needed)
- ✅ **1GB RAM free tier** (8GB on paid)
- ✅ **$5 free credit/month** - enough for 500+ hours
- ✅ **Auto-deploy on git push**
- ✅ **Faster than Vercel for this use case**

## Deploy in 60 Seconds:

### Step 1: Sign Up
1. Go to **[railway.app](https://railway.app)**
2. Click **"Start a New Project"**
3. Sign in with GitHub

### Step 2: Deploy
1. Click **"Deploy from GitHub repo"**
2. Select **`jeetshorey123/airline`**
3. Click **"Deploy Now"**

### Step 3: Done!
- Railway auto-detects Python
- Installs requirements.txt
- Runs with gunicorn
- You get a URL like: `https://airline-production-xxxx.up.railway.app`

## That's It! 🚀

**Process unlimited PDFs with 1GB upload limit!**

---

## Alternative: Run Locally (Unlimited, Free)

```bash
cd airline
pip install -r requirements.txt
python app.py
```

Open `http://localhost:5000` - Use your PC's full power!

---

## Why NOT Vercel?

| Feature | Vercel | Railway | Local |
|---------|--------|---------|-------|
| Upload Size | 4.5MB ❌ | 1GB ✅ | Unlimited ✅ |
| Timeout | 10s ❌ | None ✅ | None ✅ |
| Memory | 50MB ❌ | 1GB+ ✅ | Your RAM ✅ |
| Processing | Serverless ❌ | Full Server ✅ | Full Server ✅ |

**Vercel is fundamentally incompatible with your requirements.**

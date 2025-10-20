# Sitemap Generator - Team Setup Guide

## 🎯 For Team Members (First Time Setup)

### Step 1: Install `uv` (One-Time Only)

Choose your operating system:

**macOS/Linux:**
```bash
pip3 install uv
```

**Windows (PowerShell):**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Alternative (if you have Python):**
```bash
pip install uv
```

### Step 2: Get the Tool

Download or clone this folder to your computer. You need:
- `run_sitemap_generator.py` (the main script)
- `templates/` folder (with HTML files)

### Step 3: Run the Tool

**Option A - Direct Python (Recommended):**
```bash
python3 run_sitemap_generator.py
```

**Option B - Shell Script (Unix/Mac):**
```bash
chmod +x run.sh
./run.sh
```

**Option C - Windows:**
```cmd
python run_sitemap_generator.py
```

That's it! The first run will take ~5-10 seconds to install dependencies. Subsequent runs are instant.

---

## 🔧 Troubleshooting

### "uv: command not found"
**Fix:** Install uv (see Step 1 above)

### "No module named 'flask'"
**Fix:** You might be running with system Python instead of uv. Make sure to use:
```bash
uv run run_sitemap_generator.py
```
Or use the script as-is:
```bash
python run_sitemap_generator.py
```
### Port 5000 already in use
The app will show an error. Either:
1. Close the other app using port 5000
2. Edit the script to use a different port (change `port=5000` to `port=5001`)

### Can't access the web interface
Make sure you're opening: `http://127.0.0.1:5000` or `http://localhost:5000`

## 🆘 Need Help?

Contact: [Jimmy Lange] - [jimmy.lange@payscale.com]

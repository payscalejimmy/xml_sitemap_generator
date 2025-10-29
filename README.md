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
- `sitemap_generator.py` (the main script)
- `templates/` folder (with HTML files)
- `Launch Sitemap Generator.command` (Mac launcher)
- `Launch Sitemap Generator.bat` (Windows launcher)

### Step 2B: Add uv to your PATH (Recommended)

**macOS/Linux:**
```bash
# Add Python bin directory to PATH
echo 'export PATH="$HOME/Library/Python/3.9/bin:$PATH"' >> ~/.zshrc
# Reload your shell configuration
source ~/.zshrc
# Test if uv works
uv --version
```

**Windows:**

After installing uv, you need to add it to your PATH:

1. **Find your uv installation path** (usually one of these):
   - `%USERPROFILE%\.cargo\bin`
   - `%LOCALAPPDATA%\Programs\uv`

2. **Add to PATH using PowerShell (Recommended):**
```powershell
   # Add uv to user PATH
   $uvPath = "$env:USERPROFILE\.cargo\bin"
   [Environment]::SetEnvironmentVariable("Path", $env:Path + ";$uvPath", "User")
   
   # Restart PowerShell and test
   uv --version
```

3. **Or add manually via System Settings:**
   - Press `Win + X` and select "System"
   - Click "Advanced system settings"
   - Click "Environment Variables"
   - Under "User variables", select "Path" and click "Edit"
   - Click "New" and add: `%USERPROFILE%\.cargo\bin`
   - Click "OK" on all windows
   - Restart your terminal and test: `uv --version`

### Step 3: Run the Tool

**Option A - Double-Click Launcher (Easiest):**
- **Mac:** Double-click `Launch Sitemap Generator.command`
- **Windows:** Double-click `Launch Sitemap Generator.bat`

**Option B - Command Line:**
```bash
uv run sitemap_generator.py
```

**Option C - Traditional Python (Windows):**
```cmd
python sitemap_generator.py
```

That's it! The first run will take ~5-10 seconds to install dependencies. Subsequent runs are instant.

---

## 🔧 Troubleshooting

### "uv: command not found" (Mac/Linux)
**Fix:** 
1. Install uv (see Step 1 above)
2. Add uv to PATH (see Step 2B above)

### "uv is not recognized" (Windows)
**Fix:**
1. Make sure uv is installed
2. Add uv to PATH (see Step 2B Windows instructions)
3. Restart your terminal/PowerShell
4. Test with: `uv --version`

### "No module named 'flask'"
**Fix:** You might be running with system Python instead of uv. Make sure to use:
```bash
uv run sitemap_generator.py
```

Or use the launcher files provided.

### Port 5000 already in use
The app will show an error. Either:
1. Close the other app using port 5000
2. Edit the script to use a different port (change `port=5000` to `port=5001`)

### Can't access the web interface
Make sure you're opening: `http://127.0.0.1:5000` or `http://localhost:5000`

### Mac: "Cannot be opened because it is from an unidentified developer"
**Fix for .command file:**
1. Right-click the file and select "Open"
2. Click "Open" in the dialog
3. Or run: `chmod +x "Launch Sitemap Generator.command"`

## 🆘 Need Help?
Contact: [Jimmy Lange] - [jimmy.lange@payscale.com]

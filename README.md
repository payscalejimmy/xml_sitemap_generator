# Sitemap Generator - Team Setup Guide

[Homepage CSV File](https://payscaleinc-my.sharepoint.com/:x:/g/personal/jimmy_lange_payscale_com/ESo9q5mterdPkW-EkY-KGvcBOVyl5fq5QqAN1pjCVE2WSQ?e=ErrEDi)
[Botify Direct Input Link](https://app.botify.com/t-rex/payscale.com/crawl/explorer?context=%7B%22filter%22%3A%7B%22and%22%3A%5B%7B%22and%22%3A%5B%7B%22predicate%22%3A%22eq%22%2C%22value%22%3Atrue%2C%22field%22%3A%22compliant.is_compliant%22%7D%5D%7D%5D%7D%7D&dimensionFilterState=%7B%22selectedItemIds%22%3A%5B%22research%2F%2A%22%5D%2C%22unselectedItemIds%22%3A%5B%5D%2C%22selectedOptionId%22%3A%22segments.research_countries.value%22%7D&comparisonAnalysisSlug=20250912&analysisSlug=20251010&explorerFilter=%7B%22columns%22%3A%5B%22compliant.is_compliant%22%5D%7D)
[OneDrive Repo](https://payscaleinc-my.sharepoint.com/:f:/g/personal/jimmy_lange_payscale_com/Eg7HQn8oDstDvEML09wsVV0BOhzel_ZbORwJhPHnSgaL-A?e=hiCxjU)

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

---

## 🚀 Creating Click-to-Launch Apps

### For Mac: AppleScript Application

**One-time setup (5 minutes):**

1. Open **Script Editor** (Press `Cmd + Space`, type "Script Editor", press Enter)

2. Copy and paste this code:
   ```applescript
   tell application "Terminal"
       activate
       do script "cd " & quoted form of (POSIX path of (do shell script "dirname " & quoted form of POSIX path of (path to me))) & " && uv run sitemap_generator.py"
   end tell
   ```

3. Click **File → Save** (or press `Cmd + S`)

4. In the save dialog:
   - **Save As:** `Launch Sitemap Generator`
   - **Where:** Choose the same folder where `sitemap_generator.py` is located
   - **File Format:** Change from "Script" to **"Application"**
   - Click **Save**

5. **Done!** You now have a `Launch Sitemap Generator.app` that you can double-click to run the tool.

**Optional - Add a custom icon:**
- Find an icon you like (PNG or ICNS format)
- Right-click `Launch Sitemap Generator.app` → Get Info
- Drag your icon image onto the small icon in the top-left of the Get Info window

---

### For Windows: Batch Script

**One-time setup (2 minutes):**

1. Open **Notepad**

2. Copy and paste this code:
   ```batch
   @echo off
   title Sitemap Generator
   cd /d "%~dp0"
   echo Starting Sitemap Generator...
   echo.
   uv run sitemap_generator.py
   echo.
   echo Sitemap Generator has stopped.
   pause
   ```

3. Click **File → Save As**

4. In the save dialog:
   - **File name:** `Launch Sitemap Generator.bat` (include the `.bat` extension)
   - **Save as type:** Change to **"All Files (*.*)"**
   - **Where:** Choose the same folder where `sitemap_generator.py` is located
   - Click **Save**

5. **Done!** You can now double-click `Launch Sitemap Generator.bat` to run the tool.

**Optional - Create a desktop shortcut:**
- Right-click `Launch Sitemap Generator.bat` → Create shortcut
- Drag the shortcut to your desktop
- Right-click the shortcut → Properties → Change Icon (choose an icon you like)

---

## 🎮 Using the Tool

### Easiest Method: Double-Click the Launcher

**Mac:** Double-click `Launch Sitemap Generator.app`  
**Windows:** Double-click `Launch Sitemap Generator.bat`

A terminal window will open and start the Flask server. When you see:
```
* Running on http://127.0.0.1:5000
```

Open your web browser and go to: **http://localhost:5000**

**To stop the server:** Close the terminal window or press `Ctrl + C`

---

### Alternative: Command Line

If you prefer using the terminal:

```bash
uv run sitemap_generator.py
```

---

## 🔧 Troubleshooting

### "uv: command not found" (Mac/Linux)
**Fix:** 
1. Install uv (see Step 1 above)
2. Add uv to PATH (see Step 2B above)
3. Restart your terminal

### "uv is not recognized" (Windows)
**Fix:**
1. Make sure uv is installed
2. Add uv to PATH (see Step 2B Windows instructions)
3. **Restart your computer** (important!)
4. Test with: `uv --version`

### "No module named 'flask'"
**Fix:** You might be running with system Python instead of uv. Make sure to use the launcher apps or run:
```bash
uv run sitemap_generator.py
```

### Mac: Launcher opens Terminal but nothing happens
**Fix:** Make sure `uv` is in your PATH:
1. Open Terminal
2. Type `uv --version` and press Enter
3. If you get an error, follow Step 2B above to add uv to PATH

### Windows: Black window flashes and closes immediately
**Fix:** This means there's an error. To see what it is:
1. Open Command Prompt (search for "cmd" in Start menu)
2. Drag `Launch Sitemap Generator.bat` into the Command Prompt window
3. Press Enter
4. Read the error message (usually means `uv` is not in PATH)

### Port 5000 already in use
The app will show an error. Either:
1. Close the other app using port 5000
2. Edit `sitemap_generator.py` to use a different port (change `port=5000` to `port=5001`)

### Can't access the web interface
Make sure you're opening: `http://127.0.0.1:5000` or `http://localhost:5000`

### Mac: "Launch Sitemap Generator.app is damaged and can't be opened"
**Fix:**
1. Open Terminal
2. Run: `xattr -cr "/path/to/Launch Sitemap Generator.app"`
3. Or: Right-click the app → Open (then click "Open" in the dialog)

---

## 📝 First Time Running

The first time you run the tool, `uv` will:
1. Create a virtual environment (5-10 seconds)
2. Install Flask and other dependencies (5-10 seconds)

After that, subsequent launches are instant! The terminal will show:
```
* Running on http://127.0.0.1:5000
* Press CTRL+C to quit
```

This means the server is ready. Open your browser to http://localhost:5000 and start generating sitemaps!

---

## 🆘 Need Help?
Contact: [Jimmy Lange] - [jimmy.lange@payscale.com]

---

## 🎁 Bonus: What's Included

```
sitemap-generator/
├── sitemap_generator.py          # Main Flask application
├── templates/                     # HTML templates
│   ├── index.html
│   └── result.html
├── Launch Sitemap Generator.app   # Mac launcher (you create this)
├── Launch Sitemap Generator.bat   # Windows launcher (you create this)
└── README.md                      # This file
```

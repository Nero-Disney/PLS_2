# PySide6 GUI Applications in GitHub Codespaces

GitHub Codespaces runs on headless, cloud-hosted Linux virtual machines without physical display hardware. This repository contains the configuration needed to run, render, and interact with **PySide6 (Qt6)** graphical applications directly inside your web browser.

---

## 🛠️ Prerequisites

The system requires a virtual X11 display buffer (`Xvfb`), a lightweight window manager (`Fluxbox`), and a web-streaming bridge (`noVNC`).

If you haven't installed them yet, open your Codespaces terminal and run:
```bash
sudo apt-get update && sudo apt-get install -y \
    xvfb x11vnc fluxbox websockify novnc \
    libgl1 libglx-mesa0 libegl1 libdbus-1-3 \
    libxkbcommon-x11-0 libfontconfig1 libxcb-cursor0 \
    libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
    libxcb-randr0 libxcb-render-util0 libxcb-shape0 \
    libxcb-xfixes0 libxcb-xinerama0
```

Make sure your Python virtual environment is active and `PySide6` is installed:
```bash
source venv/bin/activate
pip install PySide6
```

---

## 🚀 Quick Start (Automated Script)

An automation script (`start_gui.sh`) is provided to launch all background display server components automatically.

### Step 1: Make the script executable
```bash
chmod +x start_gui.sh
```

### Step 2: Run the initialization script
```bash
./start_gui.sh
```
*Note: The script will load background workers and keep your terminal interactive.*

### Step 3: Expose the Web Browser Desktop
1. Look at the bottom panel of your VS Code interface and click the **Ports** tab.
2. Locate port **`6080`** (if missing, click *Forward a Port* and type `6080`).
3. Right-click port `6080` and change **Port Visibility** to **Public**.
4. Click the 🌐 (**Open in Browser**) icon next to port `6080`.
5. In the new browser tab that opens, click the blue **Connect** button. You will see a blank desktop.

### Step 4: Run your PySide6 app
Go back to your Codespaces terminal and run your code:
```bash
python your_pyside_script.py
```
Switch over to your noVNC browser tab to see and interact with your graphical application!

---

## ⚠️ Understanding Terminal "Pseudo-Errors"

When running the initialization script or starting display elements manually, the terminal will print a massive wall of text. **These are completely harmless and non-fatal.** You can ignore them:

| Terminal Warning Text | Why It Happens | Why It Is Safe to Ignore |
| :--- | :--- | :--- |
| `_XSERVTransmkdir: ERROR: euid != 0...` | The X-server is trying to make a root-level system directory in `/tmp`. | Codespaces isolates you as a standard developer user. The server automatically falls back to an alternative user-owned folder and works perfectly. |
| `The XKEYBOARD keymap compiler (xkbcomp) reports...` | The virtual keyboard is searching for physical laptop hotkeys (e.g., camera toggle, media keys). | Your virtual cloud computer doesn't have physical media keys. The server explicitly prints that these warnings are non-fatal. |
| `Failed to read: session.ignoreBorder ... Setting default value` | Fluxbox window manager is looking for a custom UI/theme preferences profile. | Because it is running in a fresh cloud instance, a theme profile doesn't exist yet. It automatically builds and falls back to default clean styling. |

---

## 🛑 Stopping the Server

If you ever need to stop the background display services and clear up the network ports, run:
```bash
killall Xvfb x11vnc fluxbox websockify
```

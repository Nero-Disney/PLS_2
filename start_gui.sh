#!/bin/bash

# ==============================================================================
# CODESPACES PYSIDE6 GRAPHICAL ENVIRONMENT INITIALIZATION SCRIPT
# ==============================================================================
# This script sets up a headless X11 display buffer, a window manager,
# a VNC server, and a web stream to allow PySide6 apps to run in the browser.
# ==============================================================================

echo "🔄 Initializing virtual display server..."

# 1. Clear out any old lock files from previous crashes to prevent port conflicts
rm -f /tmp/.X1-lock /tmp/.X11-unix/X1

# 2. Start Xvfb (X Virtual Framebuffer)
# This simulates a physical monitor in memory (Display :1, Res: 1280x720, 24-bit color).
# The '&' runs it in the background so the script can continue.
Xvfb :1 -screen 0 1280x720x24 &

# Give Xvfb one second to initialize before moving on
sleep 1

# 3. Export the DISPLAY variable
# This tells PySide6 and the system exactly where to send graphical windows.
export DISPLAY=:1
echo "🖥️  DISPLAY variable set to: $DISPLAY"

# 4. Launch Fluxbox Window Manager
# Without a window manager, your PySide6 windows won't have title bars, close 
# buttons, or the ability to minimize/drag across the screen.
echo "🎨 Starting Fluxbox window manager..."
fluxbox &

# Give Fluxbox a moment to create default configs
sleep 1

# 5. Start x11vnc Server
# This captures the virtual display screen buffer and shares it via the standard 
# VNC protocol on local port 5900.
# Flags: -nopw (no password), -forever (don't exit after a disconnect), -shared (allow multiple viewers)
echo "🔒 Launching VNC server..."
x11vnc -display :1 -nopw -forever -shared &

# 6. Start Websockify (noVNC Bridge)
# HTML5 Web browsers cannot read raw VNC data natively. Websockify converts the 
# VNC stream from port 5900 into a secure WebSocket stream on port 6080.
echo "🌐 Launching browser-accessible noVNC bridge on port 6080..."
websockify --web=/usr/share/novnc 6080 localhost:5900 &

echo "=============================================================================="
echo "✅ SETUP SUCCESSFUL!"
echo "=============================================================================="
echo "👉 STEP 1: Go to your Codespaces 'Ports' tab."
echo "👉 STEP 2: Right-click port 6080, and change Port Visibility to PUBLIC."
echo "👉 STEP 3: Click the globe icon on port 6080 to open the desktop in your browser."
echo "👉 STEP 4: Run your application in this terminal: python your_script.py"
echo "=============================================================================="

# This keeps our terminal interactive so you can run your PySide6 script right away.
$SHELL

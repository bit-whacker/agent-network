# Docker Desktop Troubleshooting Guide for Windows

## Error: "Docker Desktop is unable to start"

This is a common Windows issue. Try these solutions in order:

---

## Quick Fixes (Try First)

### Fix 1: Simple Restart
1. Close Docker Desktop completely (right-click system tray icon → Quit)
2. Wait 10 seconds
3. Open Docker Desktop again from Start Menu
4. Wait for green "Docker Desktop is running" icon

### Fix 2: Run as Administrator
1. Right-click Docker Desktop in Start Menu
2. Select "Run as administrator"
3. Click "Yes" when Windows asks for permission

---

## Enable WSL 2 (Most Common Solution)

### Check if WSL 2 is installed:
```powershell
# Run PowerShell as Administrator
wsl --list --verbose
```

### If WSL 2 is not installed:
```powershell
# Run PowerShell as Administrator
wsl --install
wsl --set-default-version 2
```

Then **restart your computer**.

### Update WSL kernel (if needed):
1. Download from: https://aka.ms/wsl2kernel
2. Install the update
3. Restart computer
4. Start Docker Desktop

---

## Check Virtualization

### Verify virtualization is enabled:
```powershell
# Run PowerShell as Administrator
systeminfo
```

Look for this section:
```
Hyper-V Requirements:
    VM Monitor Mode Extensions: Yes
    Virtualization Enabled In Firmware: Yes  ← Should be "Yes"
    Second Level Address Translation: Yes
    Data Execution Prevention Available: Yes
```

### If "Virtualization Enabled In Firmware" is "No":

1. **Restart computer**
2. **Enter BIOS Setup**:
   - Press F2, F10, Del, or Esc during boot (varies by manufacturer)
   - Look for manufacturer logo on startup to see which key
3. **Find Virtualization Settings**:
   - Usually under "Advanced" or "CPU Configuration"
   - Look for:
     - Intel: "Intel VT-x" or "Virtualization Technology"
     - AMD: "AMD-V" or "SVM Mode"
4. **Enable it**
5. **Save and Exit** (usually F10)
6. **Restart computer**
7. **Start Docker Desktop**

---

## Enable Hyper-V

### Method 1: PowerShell (Recommended)
```powershell
# Run PowerShell as Administrator
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All
```

Then restart when prompted.

### Method 2: Windows Features
1. Open "Turn Windows features on or off" (search in Start Menu)
2. Check these boxes:
   - ✅ Hyper-V
   - ✅ Windows Hypervisor Platform
   - ✅ Virtual Machine Platform
   - ✅ Windows Subsystem for Linux
3. Click OK
4. Restart when prompted

---

## Reset Docker Desktop

### If Docker Desktop opens but doesn't work:
1. Open Docker Desktop
2. Click Settings (gear icon)
3. Go to "Troubleshoot" section
4. Click "Reset to factory defaults"
5. Click "Reset" to confirm
6. Wait for reset to complete
7. Docker will restart automatically

---

## Reinstall Docker Desktop

### Complete clean reinstall:

1. **Uninstall Docker Desktop**:
   - Settings → Apps → Docker Desktop → Uninstall
   - Or Control Panel → Programs → Uninstall

2. **Delete Docker folders** (if they exist):
   ```
   C:\Program Files\Docker
   C:\ProgramData\Docker
   C:\Users\YourUsername\.docker
   ```

3. **Restart computer**

4. **Download fresh installer**:
   - https://www.docker.com/products/docker-desktop/

5. **Install Docker Desktop**:
   - ✅ Check "Use WSL 2 instead of Hyper-V"
   - Click "Ok" and wait for installation

6. **Restart computer again**

7. **Start Docker Desktop**

---

## Check System Requirements

Docker Desktop for Windows requires:

✅ **Windows 10/11**:
   - Windows 10 version 1903 or higher
   - Windows 11 any version

✅ **WSL 2**:
   - Required for Docker Desktop

✅ **Virtualization**:
   - Must be enabled in BIOS

✅ **Hyper-V**:
   - Windows 10/11 Pro, Enterprise, or Education
   - (Home edition uses WSL 2 instead)

✅ **RAM**: At least 4GB (8GB recommended)

### Check Windows version:
```powershell
winver
```

---

## Still Not Working?

### Check Docker Desktop logs:
```
C:\Users\YourUsername\AppData\Local\Docker\log.txt
```

### Common error messages and fixes:

**"WSL 2 installation is incomplete"**
→ Run: `wsl --install` then restart

**"Hardware assisted virtualization and data execution protection must be enabled in the BIOS"**
→ Enable virtualization in BIOS (see above)

**"Docker Desktop requires a newer WSL kernel version"**
→ Download: https://aka.ms/wsl2kernel

**"Docker failed to initialize"**
→ Reset Docker Desktop (see above)

**"The process cannot access the file because it is being used by another process"**
→ Kill Docker processes:
```powershell
# Run PowerShell as Administrator
taskkill /F /IM docker.exe
taskkill /F /IM com.docker.service
```
Then restart Docker Desktop

---

## Alternative: Use Docker without Docker Desktop

If Docker Desktop absolutely won't work, you can use Docker in WSL 2 directly:

### Install Docker in WSL 2:
```bash
# Open WSL 2 terminal (Ubuntu)
sudo apt update
sudo apt install docker.io docker-compose
sudo service docker start
sudo usermod -aG docker $USER
```

Then run the application from WSL:
```bash
cd /mnt/c/Users/YourUsername/Documents/agent-network
docker-compose up -d
```

---

## After Docker Desktop is Working

Once Docker Desktop shows "Docker Desktop is running" (green icon):

```powershell
# Test Docker is working
docker --version
docker run hello-world

# If that works, start your application
cd C:\Users\Hassan\Documents\agentic_networking\agent-network
.\start.ps1
```

---

## Prevention Tips

✅ Don't close Docker Desktop from the X button - use "Quit Docker Desktop"
✅ Keep Windows updated
✅ Keep Docker Desktop updated
✅ Don't run too many VMs or virtualization software simultaneously
✅ Ensure you have enough RAM available

---

## Quick Diagnostic Commands

Run these to check your setup:

```powershell
# Check Windows version
winver

# Check WSL version
wsl --list --verbose

# Check if virtualization is enabled
systeminfo | findstr /C:"Virtualization"

# Check Docker version (if Docker is running)
docker --version
docker-compose --version

# Test Docker
docker run hello-world
```

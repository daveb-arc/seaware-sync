# 🐳 Windows Dev Container for Uncruise Projects (Docker Compose)

This setup provides a **Windows-based Docker development environment** using Docker Compose. It includes:

- Java 17 (Adoptium)
- Python 3.12
- Git
- Salesforce Data Loader v64.0.2
- Cloned project repositories into `C:\repo` inside the container

Use this container to run batch scripts, work across multiple Salesforce-related repositories, and develop in a consistent Windows environment.

---

## ✅ Prerequisites

- **Windows 10 or 11 (Pro, Enterprise, or Education)**
- [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop)
- Docker must be running in **Windows Containers mode**

---

### 🧰 If DNS resolution fails during image build (e.g., GitHub downloads break)

You may need to manually set Docker’s DNS settings to allow Windows containers to access the internet:

1. Open this file (create it if it doesn’t exist):

   ```
   C:\ProgramData\Docker\config\daemon.json
   ```

2. If the file exists, **merge** the following `"dns"` block into it. Otherwise, use this content:

   ```json
   {
     "dns": ["8.8.8.8", "1.1.1.1"]
   }
   ```

   Example with other existing settings:

   ```json
   {
     "experimental": false,
     "hosts": [
       "npipe:////./pipe/docker_engine_windows"
     ],
     "dns": ["8.8.8.8", "1.1.1.1"]
   }
   ```

3. **Restart Docker Desktop completely**:
   - Right-click the Docker whale icon → **Quit Docker Desktop**
   - Launch it again from the Start Menu

4. Verify DNS works by running:

   ```powershell
   docker run --rm mcr.microsoft.com/windows/servercore:20H2 powershell -Command "Resolve-DnsName github.com"
   ```

   You should see an IP address in the output.

---

### 🔄 How to Switch Docker to Windows Containers

1. **Right-click** the Docker icon in the system tray  
   → Click **"Switch to Windows containers…"**

2. If the option is **missing**, follow these steps:

#### 🛠️ Option 1: Reinstall Docker Desktop with Windows container support

- Uninstall Docker Desktop from **Apps & Features**.
- Download the latest installer from:  
  👉 https://www.docker.com/products/docker-desktop
- During installation, make sure to:
  - ✅ **Select the option** to **"Enable Windows containers"** (it's typically a checkbox in the setup wizard).
  - ✅ **Enable Hyper-V** if prompted — it's required for Windows container support.

#### 🛠️ Option 2: Manually enable Windows container features

- ✅ Confirm you’re on **Windows 10/11 Pro**
- ✅ Run PowerShell **as Administrator** and enable required features:

  ```powershell
  Enable-WindowsOptionalFeature -Online -FeatureName containers -All
  Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All
  ```

  Reboot if prompted.

- 🔄 Then force Docker to switch using the CLI:

  ```powershell
  & "$Env:ProgramFiles\Docker\Docker\DockerCli.exe" -SwitchDaemon
  ```

- ✅ Run `docker info` and verify the output contains `OSType: windows`

---

- PowerShell or any terminal
- (Optional) [Visual Studio Code](https://code.visualstudio.com/) with Remote Containers extension (for attaching to the running container)

---

## 🚀 Setup (Step-by-Step)

### 1. Clone the main repo

```powershell
git clone https://github.com/daveb-arc/seaware-sync.git
cd seaware-sync
```

### 2. Build and start the container

```powershell
docker-compose -f .devcontainer-windows/docker-compose.yml up --build
```

> ℹ️ This command builds the Docker image and starts the container with everything pre-installed.  
> 🧠 **Tip:** You only need `--build` the **first time** or if you've changed the Dockerfile.  
> For everyday development, simply use:

```powershell
docker-compose -f .devcontainer-windows/docker-compose.yml up
```

---

## 🛠️ Development Workflow

Once the container is running:

- **Attach a terminal** to the container using Docker Dashboard or:

  ```powershell
  docker exec -it uncruise-dev powershell
  ```

- Your code will be located inside the container at:

  ```
  C:\repo
  ```

- Run any internal scripts or batch files as needed.

---

## 📂 Project Structure

```text
seaware-sync/
├── .devcontainer-windows/
│   ├── docker-compose.yml         # Docker Compose config for Windows containers
│   └── Dockerfile                 # Dockerfile for building the Windows image
├── repo/                          # Your local source code (mounted into container)
├── scripts/
├── batch/
└── README.md                      # This file
```

---

## 🧹 Cleanup

To stop and remove the container:

```powershell
docker-compose -f .devcontainer-windows/docker-compose.yml down
```

To remove all containers/images:

```powershell
docker system prune -a
```

---

## 📎 Notes

- This setup is tailored for **Windows containers** and won’t run under Linux container mode.
- If you're using **Linux containers by default**, switch before continuing (see instructions above).
- Ensure Docker Desktop is up-to-date for best compatibility with Windows-based images.

---

Made with ❤️ for Uncruise development teams.

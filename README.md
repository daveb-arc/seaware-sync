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

## 🧰 If DNS resolution fails during image build

Update or create:

```
C:\ProgramData\Docker\config\daemon.json
```

```json
{
  "dns": ["8.8.8.8", "1.1.1.1"]
}
```

Restart Docker Desktop after saving.

Verify with:

```powershell
docker run --rm mcr.microsoft.com/windows/servercore:20H2 powershell -Command "Resolve-DnsName github.com"
```

---

## 🔄 Switch Docker to Windows Containers

1. Right-click Docker whale icon → **Switch to Windows containers…**

If missing, do:

```powershell
Enable-WindowsOptionalFeature -Online -FeatureName containers -All
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All
```

Reboot if prompted. Then:

```powershell
& "$Env:ProgramFiles\Docker\Docker\DockerCli.exe" -SwitchDaemon
```

Verify:

```powershell
docker info
```

Should show `OSType: windows`.

---

## 🚀 Setup (Step-by-Step)

### 1. Clone and arrange your files

```powershell
git clone https://github.com/daveb-arc/seaware-sync.git
cd C:\repo
```

Ensure this layout:

```
C:\repo\
├── seaware-sync\
│   ├── docker-compose.yml
│   ├── Dockerfile
│   ├── dependencies\
│   │   └── dataloader_v64.0.2\  ← Already extracted
├── Salesforce-Importer\
├── Salesforce-Exporter\
├── Salesforce-Importer-Private\
├── Salesforce-Exporter-Private\
```

---

### 2. Build the Docker image (from repo root)

```powershell
$Env:DOCKER_BUILDKIT = 1
docker build --network="Default Switch" --no-cache -t uncruise-dev-win -f seaware-sync\Dockerfile seaware-sync
```

---

### 3. Start container using Compose (from repo root)

```powershell
docker-compose -f seaware-sync\docker-compose.yml up
```

> This uses the versioned Compose file inside `seaware-sync`, but can be launched from `C:\repo`.

---

## 💻 Interact with the Container

If you're at this prompt:

```
PS C:\repo\seaware-sync>
```

You're inside the container.

To confirm:

```powershell
$env:COMPUTERNAME
```

Or:

```powershell
C:\Windows\System32\hostname.exe
```

To interact via terminal (recommended):

```powershell
docker-compose -f seaware-sync\docker-compose.yml run uncruise-dev
```
---

## 📂 Project Structure

```text
C:\repo\
├── seaware-sync\
│   ├── docker-compose.yml
│   ├── Dockerfile
│   ├── dependencies\
│   │   └── dataloader_v64.0.2\
│   └── README.md
├── Salesforce-Importer\
├── Salesforce-Exporter\
├── Salesforce-Importer-Private\
├── Salesforce-Exporter-Private\
```

---

## 🧹 Cleanup

Stop and remove the container:

```powershell
docker-compose -f seaware-sync\docker-compose.yml down
```

Remove all containers/images:

```powershell
docker system prune -a
```

---

## 📎 Notes

- This setup is for **Windows containers** (not Linux containers).
- `docker-compose.yml` stays versioned under `seaware-sync`.
- All build/run commands should be run from `C:\repo`.

---

Sure! Here's the **"Run Sync Process"** section in Markdown format, ready for you to copy and paste into your GitHub README:

---

## 🚀 Run Sync Process

### ✅ 1. Pull latest changes from all 5 repos

```powershell
cd C:\repo
git -C Salesforce-Importer pull
git -C Salesforce-Exporter pull
git -C Salesforce-Importer-Private pull
git -C Salesforce-Exporter-Private pull
git -C seaware-sync pull
```

---

### ✅ 2. Launch the container in VS Code

Attach to the dev container following the instructions in this README.

---

### ✅ 3. Initialize the Seaware import

In VS Code’s integrated PowerShell terminal:

```powershell
& "C:\repo\Salesforce-Importer-Private\Clients\SEAWARE-BOOKINGS\importer-docker.bat" Bookings Prod -interactivemode
```

---

### ✅ 4. Run production sync scripts

From the `docker` folder:

```powershell
& "C:\repo\Salesforce-Importer-Private\Execute\SEAWARE\docker\salesforce-import-bookings.bat"
```

This ensures the production sync logic is preserved and not altered.

---

### ✅ 5. What gets done

* **Exports from Salesforce →**
  `C:\repo\Salesforce-Exporter-Private\Clients\SEAWARE-BOOKINGS\…\Export`
* **Exports from Seaware →**
  `C:\repo\seaware-sync\output_csv`

---

### ✅ 6. Copy results from container to host

1. Find the running container name:

   ```powershell
   docker ps
   ```

2. Copy files to Windows host:

   ```powershell
   $cid = "seaware-sync-uncruise-dev-1"

   docker cp "$cid:`"C:\repo\Salesforce-Exporter-Private\Clients\SEAWARE-BOOKINGS\Salesforce-Exporter\Clients\SEAWARE-BOOKINGS\Export`" \
       "C:\repo\Salesforce-Exporter-Private\Clients\SEAWARE-BOOKINGS\Salesforce-Exporter\Clients\SEAWARE-BOOKINGS\Export"

   docker cp "$cid:`"C:\repo\seaware-sync\output_csv`" \
       "C:\repo\seaware-sync\output_csv"
   ```

These commands overwrite any existing files on the host with the latest exports from the container.

---

*Updated: July 12, 2025*

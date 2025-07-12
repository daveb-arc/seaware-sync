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
docker build -t uncruise-dev-win -f seaware-sync\Dockerfile .
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

*Updated: July 12, 2025*

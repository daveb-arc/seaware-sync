# .devcontainer-windows/Dockerfile

FROM mcr.microsoft.com/windows/servercore:20H2

SHELL ["powershell", "-Command"]

# Install Git
RUN Invoke-WebRequest -Uri "https://github.com/git-for-windows/git/releases/download/v2.43.0.windows.1/Git-2.43.0-64-bit.exe" -OutFile git-installer.exe ; \
    Start-Process .\git-installer.exe -ArgumentList '/VERYSILENT','/NORESTART' -Wait ; \
    Remove-Item git-installer.exe

# Install Python
RUN Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe" -OutFile python-installer.exe ; \
    Start-Process .\python-installer.exe -ArgumentList '/quiet InstallAllUsers=1 PrependPath=1' -Wait ; \
    Remove-Item python-installer.exe

# Install Java (AdoptOpenJDK)
RUN Invoke-WebRequest -Uri "https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.10%2B7/OpenJDK17U-jdk_x64_windows_hotspot_17.0.10_7.msi" -OutFile jdk.msi ; \
    Start-Process msiexec.exe -ArgumentList '/i','jdk.msi','/quiet','/norestart' -Wait ; \
    Remove-Item jdk.msi

ENV JAVA_HOME="C:\\Program Files\\Eclipse Adoptium\\jdk-17.0.10.7-hotspot"
ENV PATH="$env:JAVA_HOME\\bin;$env:PATH"

# Create repo directory and clone GitHub repos
RUN New-Item -ItemType Directory -Path C:\repo ; \
    Set-Location C:\repo ; \
    git clone https://github.com/daveb-arc/seaware-sync ; \
    git clone https://github.com/Uncruise/Salesforce-Importer ; \
    git clone https://github.com/Uncruise/Salesforce-Importer-Private ; \
    git clone https://github.com/Uncruise/Salesforce-Exporter ; \
    git clone https://github.com/Uncruise/Salesforce-Exporter-Private

# Install Salesforce Data Loader
RUN Invoke-WebRequest -Uri "https://a.sfdcstatic.com/developer-website/media/dataloader/dataloader_v64.0.2.zip" -OutFile C:\\dataloader.zip ; \
    Expand-Archive -Path C:\\dataloader.zip -DestinationPath C:\\DataLoader ; \
    Remove-Item C:\\dataloader.zip

WORKDIR C:\\repo

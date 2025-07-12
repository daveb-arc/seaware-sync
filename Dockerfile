# seaware-sync/Dockerfile

FROM mcr.microsoft.com/windows/servercore:20H2

SHELL ["powershell", "-Command"]

# Install Python
COPY seaware-sync/dependencies/python-3.12.0-amd64.exe python-installer.exe
RUN Start-Process .\python-installer.exe -ArgumentList '/quiet InstallAllUsers=1 PrependPath=1' -Wait ; \
    Remove-Item python-installer.exe

# Install Java
COPY seaware-sync/dependencies/OpenJDK17U-jdk_x64_windows_hotspot_17.0.10_7.msi jdk.msi
RUN Start-Process msiexec.exe -ArgumentList '/i','jdk.msi','/quiet','/norestart' -Wait ; \
    Remove-Item jdk.msi

# Set JAVA_HOME
ENV JAVA_HOME="C:\\Program Files\\Eclipse Adoptium\\jdk-17.0.10.7-hotspot"
ENV PATH="C:\\Program Files\\Eclipse Adoptium\\jdk-17.0.10.7-hotspot\\bin;%PATH%"

# Copy cloned Git repositories into the container
COPY Salesforce-Importer C:/repo/Salesforce-Importer
COPY Salesforce-Exporter C:/repo/Salesforce-Exporter
COPY Salesforce-Importer-Private C:/repo/Salesforce-Importer-Private
COPY Salesforce-Exporter-Private C:/repo/Salesforce-Exporter-Private
COPY seaware-sync C:/repo/seaware-sync

# Copy pre-extracted Salesforce Data Loader
COPY seaware-sync/dependencies/dataloader_v64.0.2 C:/dataloader_v64.0.2

# Set working directory
WORKDIR C:/repo/seaware-sync

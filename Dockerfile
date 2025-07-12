# seaware-sync/Dockerfile
# escape=\

FROM mcr.microsoft.com/windows/servercore:20H2
SHELL ["powershell", "-Command"]

# 1️⃣ Install Liberica JRE 17 from local ZIP
COPY seaware-sync/dependencies/bellsoft-jre17.0.15+10-windows-amd64.zip jre.zip
RUN Expand-Archive jre.zip -DestinationPath C:\Java\jre; \
    Remove-Item jre.zip

ENV JAVA_HOME="C:\Java\jre"
ENV PATH="%JAVA_HOME%\bin;%PATH%"

# 2️⃣ Install Python 3.12
COPY seaware-sync/dependencies/python-3.12.0-amd64.exe python3-installer.exe
RUN Start-Process -FilePath .\python3-installer.exe \
    -ArgumentList '/quiet InstallAllUsers=1 PrependPath=1' -Wait; \
  Remove-Item python3-installer.exe

# 3️⃣ Install Python 2.7.18 silently
COPY seaware-sync/dependencies/python-2.7.18.amd64.msi python27.msi
RUN Start-Process -FilePath msiexec.exe \
    -ArgumentList '/i python27.msi ALLUSERS=1 ADDLOCAL=ALL /qn' -Wait; \
  Remove-Item python27.msi

# ✅ Copy cloned repositories
COPY Salesforce-Importer C:/repo/Salesforce-Importer
COPY Salesforce-Exporter C:/repo/Salesforce-Exporter
COPY Salesforce-Importer-Private C:/repo/Salesforce-Importer-Private
COPY Salesforce-Exporter-Private C:/repo/Salesforce-Exporter-Private
COPY seaware-sync C:/repo/seaware-sync

# ✅ Copy Data Loader folder
COPY seaware-sync/dependencies/dataloader_v64.0.2 C:/dataloader_v64.0.2

WORKDIR C:/repo/seaware-sync

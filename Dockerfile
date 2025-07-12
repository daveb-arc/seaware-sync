# seaware-sync/Dockerfile

FROM mcr.microsoft.com/windows/servercore:20H2
SHELL ["powershell", "-Command"]

# Download & install Liberica JRE 17 (~43 MB)
RUN Invoke-WebRequest \
    -Uri "https://download.bell-sw.com/java/17.0.12+10/bellsoft-jre17.0.12+10-windows-amd64.zip" \
    -OutFile jre.zip ; \
  Expand-Archive jre.zip -DestinationPath C:\Java\jre ; \
  Remove-Item jre.zip

ENV JAVA_HOME="C:\\Java\\jre"
ENV PATH="$env:JAVA_HOME\\bin;%PATH%"

# Install Python
COPY seaware-sync/dependencies/python-3.12.0-amd64.exe python-installer.exe
RUN Start-Process .\python-installer.exe -ArgumentList '/quiet InstallAllUsers=1 PrependPath=1' -Wait ; \
    Remove-Item python-installer.exe

RUN Invoke-WebRequest \
    -Uri "https://www.python.org/ftp/python/2.7.18/python-2.7.18.amd64.msi" \
    -OutFile python27.msi; \
    Start-Process msiexec.exe \
    -ArgumentList '/i','python27.msi','ALLUSERS=1','ADDLOCAL=ALL','/qn' \
    -Wait; \
    Remove-Item python27.msi
  
# Copy cloned repositories
COPY Salesforce-Importer C:/repo/Salesforce-Importer
COPY Salesforce-Exporter C:/repo/Salesforce-Exporter
COPY Salesforce-Importer-Private C:/repo/Salesforce-Importer-Private
COPY Salesforce-Exporter-Private C:/repo/Salesforce-Exporter-Private
COPY seaware-sync C:/repo/seaware-sync

# Copy Data Loader
COPY seaware-sync/dependencies/dataloader_v64.0.2 C:/dataloader_v64.0.2

WORKDIR C:/repo/seaware-sync

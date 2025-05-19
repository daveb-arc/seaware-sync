@echo off

set PYTHON3=C:\Users\DaveBoyce\AppData\Local\Programs\Python\Python312\
if exist C:\Python\Python313\python.exe (set PYTHON3=C:\Python\Python313\)

REM Export data from Seaware
start /b /WAIT %PYTHON3%python C:\repo\seaware-sync\query.py AGENCY SFPUSH
start /b /WAIT %PYTHON3%python C:\repo\seaware-sync\query.py AGENT SFPUSH
start /b /WAIT %PYTHON3%python C:\repo\seaware-sync\query.py CLIENT SFPUSH

echo %date:~12,4%-%date:~4,2%-%date:~7,2% %time:~0,2%:%time:~3,2%:%time:~6,2%
timeout /t 30
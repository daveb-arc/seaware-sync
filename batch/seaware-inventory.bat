set PYTHON3=C:\Users\DaveBoyce\AppData\Local\Programs\Python\Python312\
if exist C:\Python\Python313\python.exe (set PYTHON3=C:\Python\Python313\)

REM Export data from Seaware
del /F /Q C:\repo\seaware-sync\output_csv\SHIP*.csv
del /F /Q C:\repo\seaware-sync\output_csv\CABIN*.csv
del /F /Q C:\repo\seaware-sync\output_csv\CRUISE*.csv
start /b /WAIT %PYTHON3%python C:\repo\seaware-sync\query.py CRUISE QUERY

set filePath="C:\repo\seaware-sync\output_csv\SHIP.csv"
if not exist %filePath% (
	echo Error Missing - %filePath%
	goto exit
)

set filePath="C:\repo\seaware-sync\output_csv\CABIN.csv"
if not exist %filePath% (
	echo Error Missing - %filePath%
	goto exit
)

set filePath="C:\repo\seaware-sync\output_csv\CRUISE.csv"
if not exist %filePath% (
	echo Error Missing - %filePath%
	goto exit
)

:exit
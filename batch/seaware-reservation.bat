set PYTHON3=C:\Users\DaveBoyce\AppData\Local\Programs\Python\Python312\
if exist C:\Python\Python313\python.exe (set PYTHON3=C:\Python\Python313\)

REM Export data from Seaware
del /F /Q C:\repo\seaware-sync\output_csv\RESERVATION*.csv
REM start /b /WAIT %PYTHON3%python C:\repo\seaware-sync\query.py RESERVATION QUERY > C:\repo\seaware-sync\reservation.log 2>&1
start /b /WAIT %PYTHON3%python C:\repo\seaware-sync\query.py RESERVATION QUERY

set filePath="C:\repo\seaware-sync\output_csv\RESERVATION.csv"
if not exist %filePath% (
	echo Error Missing - %filePath%
	goto exit
)

set filePath="C:\repo\seaware-sync\output_csv\RESERVATION_Guests.csv"
if not exist %filePath% (
	echo Error Missing - %filePath%
	goto exit
)

set filePath="C:\repo\seaware-sync\output_csv\RESERVATION_Voyages.csv"
if not exist %filePath% (
	echo Error Missing - %filePath%
	goto exit
)

set filePath="C:\repo\seaware-sync\output_csv\RESERVATION_VoyagePackages.csv"
if not exist %filePath% (
	echo Error Missing - %filePath%
	goto exit
)

:exit
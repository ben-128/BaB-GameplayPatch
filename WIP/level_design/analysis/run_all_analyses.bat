@echo off
echo ================================================================
echo   BLAZE ^& BLADE - COMPLETE LEVEL DESIGN ANALYSIS
echo ================================================================
echo.

echo [1/3] Analyzing Chests and Contents...
echo ----------------------------------------------------------------
py -3 "%~dp0..\chests\scripts\analyze_chests.py"
echo.
echo.

echo [2/3] Analyzing Enemy Spawns...
echo ----------------------------------------------------------------
echo [SKIP] analyze_enemy_spawns.py not reorganized yet
echo.
echo.

echo [3/3] Analyzing Doors and Gates...
echo ----------------------------------------------------------------
py -3 "%~dp0..\doors\scripts\analyze_doors.py"
echo.
echo.

echo ================================================================
echo   ANALYSIS COMPLETE!
echo ================================================================
echo.
echo Files created:
echo   - chests/data/chest_analysis.json + chest_positions.csv
echo   - doors/data/door_analysis.json + door_positions.csv
echo   - coordinates/data/coordinates_*.csv
echo.
echo Next steps:
echo   1. Import CSV files into Unity (see unity/UNITY_SETUP.md)
echo   2. Review JSON files for detailed data
echo   3. Cross-reference with gameplay
echo.
pause

@echo off
echo ================================================================
echo   BLAZE ^& BLADE - COMPLETE LEVEL DESIGN ANALYSIS
echo ================================================================
echo.

echo [1/3] Analyzing Chests and Contents...
echo ----------------------------------------------------------------
py -3 analyze_chests.py
echo.
echo.

echo [2/3] Analyzing Enemy Spawns...
echo ----------------------------------------------------------------
py -3 analyze_enemy_spawns.py
echo.
echo.

echo [3/3] Analyzing Doors and Gates...
echo ----------------------------------------------------------------
py -3 analyze_doors.py
echo.
echo.

echo ================================================================
echo   ANALYSIS COMPLETE!
echo ================================================================
echo.
echo Files created:
echo   - chest_analysis.json + chest_positions.csv
echo   - spawn_analysis.json + spawn_positions.csv
echo   - door_analysis.json + door_positions.csv
echo.
echo Next steps:
echo   1. Import CSV files into Unity (see unity/UNITY_SETUP.md)
echo   2. Review JSON files for detailed data
echo   3. Cross-reference with gameplay
echo.
pause

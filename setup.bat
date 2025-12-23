@echo off

:: Activate virtual environment and load .env
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

:: Activate virtual environment
call .venv\Scripts\activate

:: Install python-dotenv to load .env
echo Loading environment variables...
.venv\Scripts\python -m pip install python-dotenv --quiet

:: Verify virtual environment is active
if "%VIRTUAL_ENV%" == "" (
    echo ERROR: Virtual environment activation failed! >&2
    exit /b 1
)

:: Load .env file
set PYTHONPATH=.
.venv\Scripts\python -c "from dotenv import load_dotenv; load_dotenv('.env')"

:: Verify PIP_REQUIRE_VIRTUALENV
if not "%PIP_REQUIRE_VIRTUALENV%" == "true" (
    echo WARNING: PIP_REQUIRE_VIRTUALENV not set. Run 'set PIP_REQUIRE_VIRTUALENV=true' manually. >&2
)

echo Setup complete. Virtual environment activated.
echo To deactivate, run: deactivate

@echo off
REM PPL Meta Mini - Dlib + Cython Docker Image Builder (Windows)
REM This script builds the enhanced Docker image with dlib and Cython optimizations

echo 🚀 PPL Meta Mini - Dlib + Cython Docker Image Builder
echo =======================================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Error: Docker is not running. Please start Docker and try again.
    pause
    exit /b 1
)

REM Check if required files exist
echo 📋 Checking required files...

if not exist "Dockerfile.cython.dlib" (
    echo ❌ Error: Required file 'Dockerfile.cython.dlib' not found!
    echo Please ensure you're in the ppl-meta-mini directory and all files are present.
    pause
    exit /b 1
)

if not exist "requirements.cython.dlib.txt" (
    echo ❌ Error: Required file 'requirements.cython.dlib.txt' not found!
    pause
    exit /b 1
)

if not exist "requirements.runtime.txt" (
    echo ❌ Error: Required file 'requirements.runtime.txt' not found!
    pause
    exit /b 1
)

if not exist "setup_cython_dlib.py" (
    echo ❌ Error: Required file 'setup_cython_dlib.py' not found!
    pause
    exit /b 1
)

if not exist "src\main.py" (
    echo ❌ Error: Required file 'src\main.py' not found!
    pause
    exit /b 1
)

echo ✅ All required files found!
echo.

REM Get system info
echo 💻 System Information:
echo   OS: Windows
for /f "tokens=*" %%a in ('docker --version') do echo   Docker Version: %%a
echo.

REM Start build
echo 🏗️ Starting Docker build...
echo ⏱️ This will take 10-20 minutes depending on your system...
echo 📦 Final image size will be approximately 850MB
echo.

REM Build with progress
docker build -f Dockerfile.cython.dlib -t ppl-meta-mini-cython-dlib:latest --progress=plain .

if %errorlevel% equ 0 (
    echo.
    echo ✅ Build completed successfully!
    echo.
    
    REM Show image info
    echo 📊 Image Information:
    docker images ppl-meta-mini-cython-dlib:latest --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
    echo.
    
    REM Test the image
    echo 🧪 Testing the built image...
    
    REM Stop any existing container
    docker stop ppl-meta-mini-dlib-test >nul 2>&1
    docker rm ppl-meta-mini-dlib-test >nul 2>&1
    
    REM Start test container
    echo Starting test container...
    docker run -d --name ppl-meta-mini-dlib-test -p 8004:8004 ppl-meta-mini-cython-dlib:latest
    
    REM Wait for service to start
    echo Waiting for service to start...
    timeout /t 10 /nobreak >nul
    
    REM Test health endpoint
    curl -s http://localhost:8004/health >nul 2>&1
    if %errorlevel% equ 0 (
        echo ✅ Service is running and responding!
        echo 🌐 Health check: http://localhost:8004/health
        echo 📚 API docs: http://localhost:8004/docs
    ) else (
        echo ⚠️ Service started but health check failed. Check logs:
        echo    docker logs ppl-meta-mini-dlib-test
    )
    
    REM Cleanup test container
    echo.
    echo 🧹 Cleaning up test container...
    docker stop ppl-meta-mini-dlib-test >nul
    docker rm ppl-meta-mini-dlib-test >nul
    
    echo.
    echo 🎉 Success! Your dlib-enhanced Cython image is ready!
    echo.
    echo 📝 Next steps:
    echo   1. Run the container:
    echo      docker run -d --name ppl-meta-mini-dlib -p 8004:8004 ppl-meta-mini-cython-dlib:latest
    echo.
    echo   2. Check health:
    echo      curl http://localhost:8004/health
    echo.
    echo   3. View API docs:
    echo      start http://localhost:8004/docs
    echo.
    echo 📖 For complete documentation, see DLIB_CYTHON_USER_GUIDE.md
    
) else (
    echo.
    echo ❌ Build failed! Please check the error messages above.
    echo.
    echo 🔍 Common solutions:
    echo   - Ensure Docker has enough memory (4GB recommended)
    echo   - Check internet connection for downloading dependencies
    echo   - Verify all required files are present
    echo   - Try building again (sometimes network issues cause temporary failures)
    echo.
    pause
    exit /b 1
)

pause

# PPL Meta Mini - Legacy Archive

This archive contains legacy files from the development and testing phases of the PPL Meta Mini service. The current production build uses **beta085** with the files at the root level.

## Archive Structure

### `/docker-legacy/`
Legacy Docker configurations from development iterations:
- `Dockerfile` - Original basic Dockerfile
- `Dockerfile.cython` - Cython compilation attempt
- `Dockerfile.cython.dlib` - Cython + dlib compilation
- `Dockerfile.nuitka` - Nuitka compilation experiment
- `Dockerfile.simple` - Simplified build approach
- `docker-compose.*.yml` - Various docker-compose configurations
- `.dockerignore.*` - Legacy dockerignore files

### `/requirements-legacy/`
Legacy dependency files from various build approaches:
- `requirements.cython.txt` - Cython build dependencies
- `requirements.cython.dlib.txt` - Cython + dlib dependencies
- `requirements.nuitka.txt` - Nuitka build dependencies
- `requirements.simple.txt` - Simplified dependencies

### `/build-scripts-legacy/`
Legacy build scripts and setup files:
- `build_nuitka.py` - Nuitka compilation script
- `setup_cython.py` - Original Cython setup script
- Various shell scripts for different build approaches

### `/docker-tar-files/`
Legacy Docker image tar files:
- `ppl-meta-mini-beta081.tar` - Beta081 image (587MB)
- `ppl-meta-mini-beta083.tar` - Beta083 image (fake tag copy)

### Root Level Files
- `cython_test_results.json` - Cython compilation test results

## Current Production Build: Beta085

The current production build uses:
- **Dockerfile**: `Dockerfile.tensorflow` (multi-stage build)
- **Requirements**: `requirements.tensorflow.txt` + `requirements.runtime.txt`
- **Build Script**: `build.sh`
- **Docker Compose**: `docker-compose.yml`
- **Setup Script**: `setup_cython_dlib.py`

## Build Evolution

1. **Beta081**: Initial working build with basic dependencies
2. **Beta083**: Discovered to be a fake tag (copy of beta081)
3. **Beta085**: Production build with complete TensorFlow + DeepFace integration

## Archive Maintenance

These files are preserved for:
- Historical reference
- Debugging legacy issues
- Understanding build evolution
- Research and development insights

**Note**: Do not use these archived files for production deployments. Always use the current beta085 configuration at the root level.

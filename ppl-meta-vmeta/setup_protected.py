from setuptools import find_packages, setup
from Cython.Build import cythonize


setup(
    name="ppl-meta-vmeta-protected",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    ext_modules=cythonize(
        [
            "src/services/embedding_service.py",
            "src/services/workflow_service.py",
            "src/services/mvr_service.py",
            "src/services/hierarchical_mvr_merger.py",
            "src/services/quality_selector.py",
        ],
        compiler_directives={"language_level": "3"},
    ),
)
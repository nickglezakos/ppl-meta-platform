from setuptools import find_packages, setup
from Cython.Build import cythonize


setup(
    name="ppl-meta-vision-protected",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    ext_modules=cythonize(
        [
            "src/extracted_face_detector.py",
            "src/distance_calculator.py",
            "src/media_processor.py",
            "src/person_objects/face_grouping_engine.py",
        ],
        compiler_directives={"language_level": "3"},
    ),
)
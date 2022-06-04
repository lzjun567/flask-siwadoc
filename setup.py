# -*- encoding: UTF-8 -*-
try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup
import io

VERSION = '0.0.1'

with io.open("README.md", encoding='utf-8') as f:
    long_description = f.read()

install_requires = open("requirements.txt").readlines()

setup(
    name="flask-siwadoc",
    version=VERSION,
    author="liuzhijun",
    author_email="lzjun567@gmail.com",
    url="https://github.com/lzjun567/flask-siwadoc",
    description="flask openapi(swagger) doc generator",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=["flask_siwadoc"],
    package_data={
        'flask_siwadoc': ['templates/*.html'],
    },
    include_package_data=True,
    license='MIT License',
    classifiers=[],
    python_requires=">=3.6",
    install_requires=install_requires,
    setup_requires=[
        'pytest-runner',
    ],
    tests_require=[
        "pytest",
    ],
)

"""
Created by Epic at 9/4/20
"""
from setuptools import setup, find_packages
import re

with open('speedcord/values.py') as f:
    version = re.search(r'^version\s*=\s*[\'"]([^\'"]*)[\'"]', f.read(), re.MULTILINE).group(1)

setup(
    name='speedcord',
    version=version,
    packages=find_packages(["README.md", "setup.py", "speedcord/*"]),
    url='https://github.com/tag-epic/speedcord',
    license='MIT',
    author='Epic',
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    install_requires=["aiohttp", "setuptools-git", "ujson"],
    package_data={"": ["*.pyi"]},
    description='A simple lightweight discord library',
    python_requires='>=3.7',
)

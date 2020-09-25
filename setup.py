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
    packages=find_packages(),
    url='https://github.com/tag-epic/speedcord',
    license='MIT',
    author='Epic',
    install_requires=["aiohttp", "setuptools-git"],
    package_data={"": ["*.pyi"]},
    description='A simple lightweight discord library',
)

"""
Created by Epic at 9/4/20
"""
from setuptools import setup
from speedcord.values import version

setup(
    name='speedcord',
    version=version,
    packages=["speedcord"],
    url='https://github.com/tag-epic/speedcord',
    license='MIT',
    author='Epic',
    install_requires=open("requirements.txt").readlines(),
    description='A simple lightweight discord library'
)

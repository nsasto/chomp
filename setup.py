from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="chomp",
    version="0.1.0",
    description="A collection of efficient and easy-to-use helpers designed to convert URLs and raw HTML into clean, structured Markdown for LLM consumption.",
    author="Nathan Sasto",
    packages=find_packages(),
    install_requires=requirements,
)
from setuptools import setup, find_packages

setup(
    name="commune-ipfs",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.68.0",
        "ipfshttpclient>=0.8.0",
        "pydantic>=2.0.0",
        "pydantic-settings>=2.0.0",
        "uvicorn>=0.15.0",
        "python-multipart",  # for file uploads
        "jinja2",  # for templates
        "aiofiles",  # for async file operations
        "python-jose[cryptography]",  # for JWT handling
    ],
    python_requires=">=3.9",
)

from setuptools import setup

setup(
    name="IALib",
    version="0.1",
    description="A library of (mostly) standalone instrument drivers",
    author="Mark Omo",
    classifiers=[  # Optional
        "Development Status :: 3 - Beta",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
    ],
    python_requires=">=3.7, <4",
    platforms=["any"],
    license="MIT",
    url="https://github.com/ferret-guy/IALib",
    install_requires=["pyvisa", "netifaces"],
)

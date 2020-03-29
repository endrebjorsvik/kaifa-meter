import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="kaifa_meter",
    version="2.0.0",
    author="Endre Bjørsvik",
    author_email="endrebjorsvik@gmail.com",
    description="Utility for reading HAN data from Kaifa electriciy meters.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/endrebjorsvik/kaifa-meter",
    packages=setuptools.find_packages(),
    install_requires=[
        'construct>=2.9', 'pyserial', 'Click', 'psycopg2-binary'
    ],
    python_requires='>=3.6',
    entry_points={
        'console_scripts': [
            'kaifa_meter=kaifa_meter.cli:cli',
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)"
        "Operating System :: OS Independent",
    ],
)

import setuptools

#-------------------------------------------------------------------------------

with open("README.md") as file:
    long_description = file.read()

setuptools.setup(
    name            ="supdoc",
    version         ="0.1.0",
    description     ="inspection-based documentation tool",
    long_description=long_description,
    url             ="https://github.com/alexhsamuel/supdoc",
    author          ="Alex Samuel",
    author_email    ="alex@alexsamuel.net",
    license         ="MIT",
    keywords        =["documentation", "docs"],
    classifiers     =[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],

    python_requires =">=3.6",
    install_requires=[
        "docutils",
        "lxml",
        "markdown",
        "pygments",
    ],

    packages        =setuptools.find_packages(exclude=[]),
    entry_points={
        'console_scripts': [
            'supdoc=supdoc.__main__:main',
        ],
    },
)


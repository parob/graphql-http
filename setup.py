import io

from setuptools import setup, find_packages

with io.open("README.md", "rt", encoding="utf8") as f:
    readme = f.read()

with io.open("VERSION") as version_file:
    version = version_file.read().strip().lower()
    if version.startswith("v"):
        version = version[1:]

setup(
    name="graphql_http_server",
    version=version,
    license="MIT",
    packages=find_packages(),
    include_package_data=True,
    author="Robert Parker",
    author_email="rob@parob.com",
    url="https://gitlab.com/parob/graphql-http-server",
    download_url=f"https://gitlab.com/parob/graphql-http-server/-/"
    f"archive/master/graphql-http-server-v{version}.zip",
    keywords=["GraphQL", "HTTPServer", "werkzeug"],
    description="HTTPServer for GraphQL.",
    long_description=readme,
    long_description_content_type="text/markdown",
    install_requires=[
        "graphql-core>=3.2.0",
        "graphql-api>=1.3.0",
        "werkzeug>=2.2.2",
        "context-helper>=1.0.2",
        "packaging>=21.3",
        "graphql-schema-diff>=1.2.4",
        "pyjwt[crypto]==2.7.0",
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)

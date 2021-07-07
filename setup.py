from setuptools import setup, find_packages

with open('./README.md', 'r') as f:
    long_description = f.read()

# Version
# Info: https://packaging.python.org/guides/single-sourcing-package-version/
# Example: https://github.com/pypa/warehouse/blob/64ca42e42d5613c8339b3ec5e1cb7765c6b23083/warehouse/__about__.py
meta_package = {}
with open('./gazouilloire/__version__.py') as f:
    exec(f.read(), meta_package)

setup(name='gazouilloire',
      version=meta_package['__version__'],
      description='Twitter stream & search API grabber',
      long_description=long_description,
      long_description_content_type='text/markdown',
      url='http://github.com/medialab/gazouilloire',
      license='GPL-3.0',
      author='Benjamin Ooghe-Tabanou',
      author_email='',
      keywords='twitter',
      python_requires='>=3.7',
      packages=find_packages(exclude=["collect*", "dist", "build"]),
      include_package_data=True,
      install_requires=[
          "elasticsearch >= 7.10.1",
          "twitwi >= 0.9.1",
          "requests",
          "pytz",
          "psutil",
          "minet >= 0.52, < 0.53",
          "future",
          "click",
          "progressbar2",
          "casanova >= 0.15.5"
      ],
      entry_points={
        'console_scripts': [
            'gazouilloire=gazouilloire.cli.__main__:main',
            'gazou=gazouilloire.cli.__main__:main'
        ]
      }
      )

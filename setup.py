from setuptools import setup, find_packages

with open('./README.md', 'r') as f:
    long_description = f.read()

def local_scheme(version):
    """Skip the local version (eg. +xyz of 0.6.1.dev4+gdf99fe2)
    to be able to upload to Test PyPI"""
    return ""

setup(name='gazouilloire',
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
      use_scm_version={"local_scheme": local_scheme},
      setup_requires=["setuptools_scm"],
      install_requires=[
          "elasticsearch >= 7.10.1, < 8.0",
          "requests",
          "psutil",
          "minet >= 0.53.8",
          "future",
          "click",
          "progressbar2"
      ],
      entry_points={
        'console_scripts': [
            'gazouilloire=gazouilloire.cli.__main__:main',
            'gazou=gazouilloire.cli.__main__:main'
        ]
      }
      )

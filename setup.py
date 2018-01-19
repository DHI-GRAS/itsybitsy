import sys
HAS_ASYNC = sys.version_info >= (3, 5)

from setuptools import setup, find_packages

if HAS_ASYNC:
    extra_dependencies = ['aiohttp', 'async_generator']
else:
    extra_dependencies = ['requests']

setup(
      name='itsybitsy',
      version='0.2',
      description='A minimal, concurrent web scraper for Python',
      author='Dion Häfner',
      author_email='dimh@dhigroup.com',
      packages=find_packages(),
      install_requires=['lxml'] + extra_dependencies,
    )

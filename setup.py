import os
import sys
from setuptools import find_packages, setup
from annotator_store import __version__

with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as readme:
    README = readme.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

TEST_REQUIREMENTS = ['pytest', 'pytest-django', 'pytest-cov']
if sys.version_info < (3, 0):
    TEST_REQUIREMENTS.append('mock')


setup(
    name='annotator_store',
    version=__version__,
    packages=find_packages(),
    include_package_data=True,
    license='Apache License, Version 2.0',
    description='Django application to act as an annotator.js 2.x annotator-store backend',
    long_description=README,
    url='https://github.com/Princeton-CDH/django-annotator-store',
    install_requires=[
        'django>1.8',
        'pytz',
        'jsonfield',
        'eulcommon',
        'six',
    ],
    setup_requires=['pytest-runner'],
    tests_require=TEST_REQUIREMENTS,
    extras_require={
        'test': TEST_REQUIREMENTS,
        'docs': ['sphinx'],
        'permissions': ['django-guardian',]
    },
    author='CDH @ Princeton',
    author_email='digitalhumanities@princeton.edu',
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 1.10',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        # NOTE: test/support other 3.x python versions?
        'Programming Language :: Python :: 3.5',
        'Development Status :: 3 - Alpha'
    ],
)

import os
from setuptools import find_packages, setup

from securegroups import __version__

with open(os.path.join(os.path.dirname(__file__), 'README.md')) as readme:
    README = readme.read()

os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

install_requires = [
    'allianceauth>=2.8.0',
]

setup(
    name='allianceauth-securegroups',
    version=__version__,
    packages=find_packages(),
    include_package_data=True,
    license='GNU General Public License v3 (GPLv3)',
    description='Alliance Auth Plugin',
    install_requires=install_requires,
    long_description=README,
    long_description_content_type='text/markdown',
    url='https://github.com/pvyParts/allianceauth-secure-groups',
    author='ak',
    author_email='ak@ak.auth',
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.6',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
)

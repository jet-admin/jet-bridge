import os
from setuptools import setup, find_packages


def read(fname):
    path = os.path.join(os.path.dirname(__file__), fname)
    try:
        file = open(path, encoding='utf-8')
    except TypeError:
        file = open(path)
    return file.read()


def get_install_requires():
    install_requires = [
        'tornado==5.1.1',
        'six',
        'jet-bridge-base==0.7.7',
    ]

    return install_requires

setup(
    name='jet-bridge',
    version=__import__('jet_bridge').VERSION,
    description='',
    long_description=read('README.md'),
    long_description_content_type='text/markdown',
    author='Denis Kildishev',
    author_email='support@jetadmin.io',
    url='https://github.com/jet-admin/jet-bridge',
    packages=find_packages(),
    license='MIT',
    classifiers=[

    ],
    zip_safe=False,
    include_package_data=True,
    install_requires=get_install_requires(),
    entry_points={
        'console_scripts': [
            'jet_bridge = jet_bridge.__main__:main',
        ],
    },
)

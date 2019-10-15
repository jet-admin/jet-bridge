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
        'sqlalchemy',
        'six',
        'requests',
        'Pillow',
        'dateparser',
        'prompt_toolkit==2.0.9',
    ]

    try:
        from collections import OrderedDict
    except ImportError:
        install_requires.append('ordereddict')

    return install_requires

setup(
    name='jet-bridge-base',
    version=__import__('jet_bridge_base').VERSION,
    description='',
    long_description=read('README.md'),
    long_description_content_type='text/markdown',
    author='Denis Kildishev',
    author_email='support@jetadmin.io',
    url='https://github.com/jet-admin/jet-bridge-base',
    packages=find_packages(),
    license='MIT',
    classifiers=[

    ],
    zip_safe=False,
    include_package_data=True,
    install_requires=get_install_requires()
)

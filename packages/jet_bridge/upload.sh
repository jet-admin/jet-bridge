#!/bin/sh
cd "$(dirname "$0")"

rm -rf dist/*
python setup.py sdist bdist_wheel
twine check dist/*
twine upload dist/*
rm -rf build/*

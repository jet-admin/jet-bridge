#!/bin/sh
cd "$(dirname "$0")"

rm -rf dist/*
python setup.py sdist bdist_wheel

VERSION=$(basename dist/jet-django-*.tar.gz | sed 's/jet-django-\(.*\)\.tar\.gz/\1/')
mv "dist/jet-django-${VERSION}.tar.gz" "dist/jet_django-${VERSION}.tar.gz"

twine check dist/*
twine upload --verbose dist/*
rm -rf build/*

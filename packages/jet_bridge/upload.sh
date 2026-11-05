#!/bin/sh
cd "$(dirname "$0")"

rm -rf dist/*
python setup.py sdist bdist_wheel

VERSION=$(basename dist/jet-bridge-*.tar.gz | sed 's/jet-bridge-\(.*\)\.tar\.gz/\1/')
mv "dist/jet-bridge-${VERSION}.tar.gz" "dist/jet_bridge-${VERSION}.tar.gz"

twine check dist/*
twine upload --verbose dist/*
rm -rf build/*

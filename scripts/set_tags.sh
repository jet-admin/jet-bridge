#!/bin/sh
cd "$(dirname "$0")"

JET_BRIDGE_BASE_VERSION="$(grep -e "VERSION" ../packages/jet_bridge_base/jet_bridge_base/__init__.py | awk '{ print substr($3, 2, length($3) - 2) }')"
JET_BRIDGE_BASE_TAG="jet_bridge_base/${JET_BRIDGE_BASE_VERSION}"
JET_BRIDGE_VERSION="$(grep -e "VERSION" ../packages/jet_bridge/jet_bridge/__init__.py | awk '{ print substr($3, 2, length($3) - 2) }')"
JET_BRIDGE_TAG="jet_bridge/${JET_BRIDGE_VERSION}"
JET_DJANGO_VERSION="$(grep -e "VERSION" ../packages/jet_django/jet_django/__init__.py | awk '{ print substr($3, 2, length($3) - 2) }')"
JET_DJANGO_TAG="jet_django/${JET_DJANGO_VERSION}"

GIT_DIR=../.git

JET_BRIDGE_BASE_TAG_ADDED=false
JET_BRIDGE_TAG_ADDED=false
JET_DJANGO_TAG_ADDED=false

if git rev-parse $JET_BRIDGE_BASE_TAG >/dev/null 2>&1 ; then
  echo "Tag is already added: ${JET_BRIDGE_BASE_TAG}"
else
  git checkout --quiet master && git tag ${JET_BRIDGE_BASE_TAG}
  echo "Added tag: ${JET_BRIDGE_BASE_TAG}"
  JET_BRIDGE_BASE_TAG_ADDED=true
fi

if git rev-parse $JET_BRIDGE_TAG >/dev/null 2>&1 ; then
  echo "Tag is already added: ${JET_BRIDGE_TAG}"
else
  git checkout --quiet master && git tag ${JET_BRIDGE_TAG}
  echo "Added tag: ${JET_BRIDGE_TAG}"
  JET_BRIDGE_TAG_ADDED=true
fi

if git rev-parse $JET_DJANGO_TAG >/dev/null 2>&1 ; then
  echo "Tag is already added: ${JET_DJANGO_TAG}"
else
  git checkout --quiet master && git tag ${JET_DJANGO_TAG}
  echo "Added tag: ${JET_DJANGO_TAG}"
  JET_DJANGO_TAG_ADDED=true
fi

if [ "$JET_BRIDGE_BASE_TAG_ADDED" = false ] && [ "$JET_BRIDGE_TAG_ADDED" = false ] && [ "$JET_DJANGO_TAG_ADDED" = false ] ; then
  exit 0
fi

read -p "Do you want to push tags? [Y/n]" -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]] ; then
  if [ "$JET_BRIDGE_BASE_TAG_ADDED" = true ] ; then
    git push origin ${JET_BRIDGE_BASE_TAG}
  fi

  if [ "$JET_BRIDGE_TAG_ADDED" = true ] ; then
    git push origin ${JET_BRIDGE_TAG}
  fi

  if [ "$JET_DJANGO_TAG_ADDED" = true ] ; then
    git push origin ${JET_DJANGO_TAG}
  fi
fi

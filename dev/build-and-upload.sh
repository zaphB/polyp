#!/usr/bin/env bash

# change dir to this script's location
cd -P -- "$(dirname -- "${BASH_SOURCE[0]}")/.."

# check if repo is clean or need commit
git update-index --refresh >/dev/null 2>&1
if ! git diff-index --quiet HEAD --; then
  echo "uncommitted changes exist in repo, commit your changes before building a release"
  exit 1
fi

if ! git pull; then
  echo "'git pull' failed, canceling."
  exit 1
fi

if ! pip install . ; then
  echo "pip install . failed, canceling."
  exit 1
fi

if ! ./dev/run-tests.sh; then
  echo "one or more unittests failed, canceling."
  exit 1
fi

# extract version info from setup.py and check if successful
ver="$(./dev/update-setup.py --clean)"
if [[ "$ver" == "" ]]; then
  echo "failed to extract current version from setup.py"
  exit 1
fi

# check if tag with current version already exists
if [[ "$(git tag | grep "v$ver")" != "" ]]; then
  echo "tag with currrent setup.py version already exists"
  exit 1
fi

# check if repo is clean or need commit
git update-index --refresh >/dev/null 2>&1
if ! git diff-index --quiet HEAD --; then
  echo "uncommitted changes exist in repo, commit your changes before building a release"
  exit 1
fi

pip install --upgrade pip build twine setuptools \
  && echo '=======================================' \
  && echo '=== updating pip, build and twine done' \
  && echo '=======================================' \
  && echo '' \
  && git tag "v$ver" \
  && git push \
  && git push --tags \
  && echo '=======================================' \
  && echo '=== building project done' \
  && echo '=======================================' \
  && echo '' \
  && rm -rf dist \
  && python -m build \
  && echo '=======================================' \
  && echo '=== building project done' \
  && echo '=======================================' \
  && echo '' \
  && python -m twine upload dist/*

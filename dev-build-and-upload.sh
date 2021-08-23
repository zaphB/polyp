#!/usr/bin/env bash

# change dir to this script's location
cd -P -- "$(dirname -- "${BASH_SOURCE[0]}")"

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

if ! python -m unittest test/*.py; then
  echo "one or more unittests failed, canceling."
  exit 1
fi

# check if repo is clean or need commit
git update-index --refresh >/dev/null 2>&1
if ! git diff-index --quiet HEAD --; then
  echo "uncommitted changes exist in repo, commit your changes before building a release"
  exit 1
fi

# extract version info from setup.py
ver="$(cat setup.py | grep 'version=' | grep -oP '\d+\.\d+\.\d+')"

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
  && python -m twine upload dist/* \
  && minor="$(cat setup.py | grep "version=" | grep -o "\.[0-9][0-9]*[^.0-9]" | grep -o "[0-9][0-9]*")" \
  && newMinor="$(echo "$minor + 1" | bc)" \
  && sed -E -i "s/version='([0-9]+\.[0-9]+\.)[0-9]+'/version='\1$newMinor'/g" setup.py

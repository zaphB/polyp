#!/usr/bin/env bash

# change dir to parent dir of this script's location
cd -P -- "$(dirname -- "${BASH_SOURCE[0]}")/.."

# run unittests
python -m unittest test/**.py || exit 1

# exit success
exit 0

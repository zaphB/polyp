#!/bin/bash

# change dir to this script's location
cd -P -- "$(dirname -- "${BASH_SOURCE[0]}")"

echo 'setting up git hooks'
git config core.hooksPath ./dev/hooks

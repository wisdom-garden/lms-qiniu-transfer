#!/bin/bash

VERSION=$(git rev-parse HEAD)

cd "$(dirname $0)"

git commit -am "${VERSION}"
git push

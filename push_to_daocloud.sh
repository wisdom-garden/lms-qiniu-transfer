#!/bin/bash

VERSION=$(git rev-parse HEAD)

cd "$(dirname $0)"

echo ${VERSION}
git status

git commit -am "${VERSION}"
git push

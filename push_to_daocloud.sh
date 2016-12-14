#!/bin/bash

VERSION=$(git rev-parse HEAD)

cd "$(dirname $0)"

git add .
git commit -m "${VERSION}"
git push

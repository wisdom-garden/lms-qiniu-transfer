#!/bin/bash

VERSION=$(git rev-parse HEAD)

cd "$(dirname $0)"

git add .
git commit -m "from lms-qiniu-transfer.git: ${VERSION}"
git push origin master

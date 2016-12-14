#!/bin/bash

CONF_FILE=/opt/conf/lms-qiniu-transfer/prod.py
APP_DIR=/opt/apps/lms-qiniu-transfer
LOG_DIR=/var/log/lms-qiniu-transfer

SPEC="00 17 * * * CONF=${CONF_FILE} python ${APP_DIR}/transfer_process.py >> ${LOG_DIR}/lms-qiniu-transfer.log 2>&1"
echo "${SPEC}" | crontab -

FROM python:3.4

COPY in_image/cn.list /etc/apt/sources.list
RUN rm -f /etc/apt/sources.list.d/* && apt-get update -q && apt-get install -y vim cron && apt-get clean

COPY in_image/build /opt/apps/lms-qiniu-transfer
RUN pip install -i https://pypi.douban.com/simple -r /opt/apps/lms-qiniu-transfer/prod-requirements.txt

COPY in_image/gen_conf_and_run.sh /tmp/

COPY in_image/add_crontab.sh /tmp/
RUN mkdir -p /var/log/lms-qiniu-transfer && /tmp/add_crontab.sh
import gzip
import io
import json
import re
import urllib.request
from datetime import datetime, timedelta
from dateutil import relativedelta

import requests
from peewee import fn
from qiniu import Auth
from qiniu.http import ResponseInfo

from src.constants import DATE_FORMAT
from src.models import TransferRecord, Org, TransferStatement


class LogEntry(object):
    def __init__(self, org_id, size):
        self.size = size
        self.org_id = org_id


class LogParser(object):
    def __init__(self):
        self.pattern = re.compile('.*&orgid=(\d+)&.*\s(\d+)\s(\d+)\s.*', re.IGNORECASE)

    def parse(self, content):
        log_entries = []
        for line in content:
            result = self.pattern.search(line.decode())
            if result:
                log_entries.append(LogEntry(int(result.group(1)), int(result.group(3))))

        return log_entries


class LogFetcher(object):
    def __init__(self, config):
        self.qiniu_log_api = QiniuLogApi(config['QINIU_STORAGE_ACCESS_KEY'],
                                         config['QINIU_STORAGE_SECRET_KEY'])
        self.domain = config['QINIU_STORAGE_BUCKET_DOMAIN']

    def fetch(self, date):
        log_file_content_list = []

        log_files = self.qiniu_log_api.get_domain_cdn_log_download_url(date, self.domain)
        for log_file in log_files:
            log_download_url = log_file.get('url')
            if log_download_url is not None:
                response = urllib.request.urlopen(log_download_url)
                compressed_file = io.BytesIO(response.read())
                decompressed_file = gzip.GzipFile(fileobj=compressed_file)
                log_file_content_list.append(decompressed_file.readlines())

        return log_file_content_list


class QiniuLogApi:
    def __init__(self, access_key, secret_key):
        self.auth = Auth(access_key, secret_key)
        self.api_url = 'http://fusion.qiniuapi.com/v2/tune/log/list'

    def _token(self):
        return "QBox " + self.auth.token_of_request(self.api_url)

    def get_domain_cdn_log_download_url(self, day, domain):
        log_files = []

        headers = {
            "Content-Type": "application/json",
            "Authorization": self._token()
        }
        body = {
            'day': day,
            'domains': domain
        }

        response = requests.post(self.api_url, data=json.dumps(body), headers=headers)
        if response.status_code == 200 and response.json().get('data') is not None \
                and response.json().get('data').get(domain) is not None:
            log_files = response.json().get('data').get(domain)
        else:
            print('log date = "{}" | '.format(day), ResponseInfo(response))

        return log_files


class TransferAccumulator(object):
    def __init__(self, log_entries, date):
        self.date = date
        self.log_entries = log_entries
        self.grouped_transfer = None

    def calc(self):
        self.grouped_transfer = self._group_logs(self.log_entries)
        return self

    def save(self):
        for _dict in self.grouped_transfer:
            TransferRecord(org_id=_dict['org_id'], size=_dict['size'], date=self.date).save()

    @staticmethod
    def _group_logs(log_entries):
        ret = {}
        for entry in log_entries:
            ret[entry.org_id] = ret.get(entry.org_id, 0) + entry.size

        return [{'org_id': org_id, 'size': size} for org_id, size in ret.items()]


class CheckList(object):
    date_window_length = 10
    last_date_offset = 2

    def __init__(self, dates):
        self._dates = dates

    @classmethod
    def build(cls):
        timezone_delta_to_utc = 8
        now = (datetime.utcnow() + timedelta(hours=timezone_delta_to_utc)).date()

        found_dates = cls._records_found_in_window(now)
        expected_dates = cls._dates_in_window(now)

        return cls(expected_dates - found_dates)

    @classmethod
    def _records_found_in_window(cls, now):
        start_date = now - timedelta(days=cls.date_window_length + cls.last_date_offset)

        records = TransferRecord.select(fn.Distinct(TransferRecord.date)) \
            .where(TransferRecord.date >= start_date, TransferRecord.date < now)

        return set([record.date.strftime(DATE_FORMAT) for record in records])

    @classmethod
    def _dates_in_window(cls, now):
        return set([(now - timedelta(days=i)).strftime(DATE_FORMAT)
                    for i in range(cls.last_date_offset, cls.date_window_length + cls.last_date_offset)])

    def output_dates(self):
        return sorted(self._dates)


class OrgTransferStatementCalculator(object):
    def __init__(self):
        self.orgs = Org.select().where(Org.flag != 1)
        self.current_month = datetime.utcnow().date().replace(day=1)
        self.last_month = self.current_month - relativedelta.relativedelta(months=1)

    def insert_current_month_record(self):
        for org in self.orgs:
            org_current_month = TransferStatement.select(). \
                where(TransferStatement.org_id == org.id, TransferStatement.month == self.current_month)

            current_org_plan = org.current_org_plan
            if len(org_current_month) == 0 and current_org_plan and not current_org_plan.expired:
                TransferStatement(org_id=org.id, month=self.current_month,
                                  plan_id=current_org_plan.plan_id).save()
            elif len(org_current_month) == 1 and current_org_plan and not current_org_plan.expired:
                TransferStatement.update(plan_id=current_org_plan.plan_id).where(
                    TransferStatement.id == org_current_month[0].id).execute()

    def update_transfer_used(self):
        for org in self.orgs:
            _current_transfer_statement = TransferStatement.select(). \
                where(TransferStatement.org_id == org.id, TransferStatement.month == self.current_month)
            _last_transfer_statement = TransferStatement.select(). \
                where(TransferStatement.org_id == org.id, TransferStatement.month == self.last_month)

            if len(_current_transfer_statement) == 1:
                current_month_transfer = self.get_org_month_transfer(org.id, self.current_month)
                TransferStatement.update(used=current_month_transfer).where(
                    TransferStatement.id == _current_transfer_statement[0].id).execute()

            if len(_last_transfer_statement) == 1:
                last_month_transfer = self.get_org_month_transfer(org.id, self.last_month)
                TransferStatement.update(used=last_month_transfer).where(
                    TransferStatement.id == _last_transfer_statement[0].id).execute()

    def get_org_month_transfer(self, org_id, month):
        current_month_start = month.replace(day=1)
        next_month_start = current_month_start - relativedelta.relativedelta(months=-1)

        result = TransferRecord.select(fn.Sum(TransferRecord.size).alias('total_size')).where(
            TransferRecord.date >= current_month_start, TransferRecord.date < next_month_start,
            TransferRecord.org_id == org_id).get()

        return 0 if result.total_size is None else result.total_size

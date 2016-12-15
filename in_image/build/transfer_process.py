import sys
from datetime import datetime
from os import path, environ

from src.constants import DATETIME_FORMAT

sys.path.append(path.dirname(path.dirname(__file__)))

from src.config import Config
from src.database import init_db
from src.services import CheckList, LogFetcher, LogParser, TransferAccumulator, OrgTransferStatementCalculator


def _load_config():
    _conf_file = environ.get('CONF')
    if not _conf_file:
        print('CONF environment variable was not given!')
        sys.exit(1)

    return Config.load_from_pyfile(_conf_file)


def run():
    check_list = CheckList.build().output_dates()
    print('{}: check list = {}'.format(datetime.now().strftime(DATETIME_FORMAT), check_list))

    for date in check_list:
        file_list = LogFetcher(config).fetch(date)
        log_entries = []
        for file in file_list:
            log_entries += LogParser().parse(file)
        if len(log_entries) > 0:
            TransferAccumulator(log_entries, date).calc().save()

    org_statement_calculator = OrgTransferStatementCalculator()
    org_statement_calculator.insert_current_month_record()
    org_statement_calculator.update_transfer_used()


def init_config_and_db():
    _config = _load_config()
    init_db(_config)
    return _config


if __name__ == '__main__':
    # command line args

    config = init_config_and_db()
    run()

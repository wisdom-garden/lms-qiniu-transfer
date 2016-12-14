from peewee import MySQLDatabase, Proxy


db = Proxy()


def init_db(config):
    mysql_db = MySQLDatabase(config['DATABASE'], host=config['HOST'], port=config['PORT'],
                             user=config['USER'], passwd=config['PASSWORD'])
    db.initialize(mysql_db)

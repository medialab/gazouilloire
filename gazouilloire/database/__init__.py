from database.mongomanager import MongoManager
from database.elasticmanager import ElasticManager


def db_manager(conf):
    """Instantiates a database according to the type, host, port & db fields of the given 'conf' argument"""
    if conf['type'] == 'mongo':
        return MongoManager(conf['host'], conf['port'], conf['db'])
    elif conf['type'] == 'elasticsearch':
        return ElasticManager(conf['host'], conf['port'], conf['db'])
    else:
        raise ValueError(
            "ERROR - database 'type' should be either 'mongo' or 'elasticsearch'")

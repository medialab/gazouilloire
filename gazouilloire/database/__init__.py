from .mongomanager import MongoManager
from .elasticmanager import ElasticManager


def db_manager(host, port, db_name, type='elasticsearch'):
    """Instantiates a database according to the type, host, port & db fields of the given 'conf' argument"""
    if type == 'mongo':
        return MongoManager(host, port, db_name)
    elif type == 'elasticsearch':
        return ElasticManager(host, port, db_name)
    else:
        raise ValueError(
            "ERROR - database 'type' should be either 'mongo' or 'elasticsearch'")

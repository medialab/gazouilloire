from database.mongomanager import MongoManager
from database.elasticmanager import ElasticManager


def db_manager(db_type, host, port, db):
    if db_type == 'mongo':
        return MongoManager(host, port, db)
    elif db_type == 'elasticsearch':
        return ElasticManager(host, port, db)
    else:
        raise ValueError(
            "ERROR - 'db_type' should be either 'mongo' or 'elasticsearch'")

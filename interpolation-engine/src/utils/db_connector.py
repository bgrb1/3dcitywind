import os
import time
from google.cloud.sql.connector import Connector as ProxyConnector
from sqlalchemy import create_engine
import pandas as pd

DB_USER = os.getenv('DB_USER')
INSTANCE_CONNECTION_NAME = os.getenv('INSTANCE_CONNECTION_NAME')


def kill_all():
    """
    Terminate all open connections
    """
    for key in engines.keys():
        engine = engines[key]
        engine.dispose()

def get_db_pw():
    """
    Helper function to retrieve DB password from secret manager
    """
    PROJECT_ID = os.getenv('PROJECT_ID')
    SECRET_ID = os.getenv('SECRET_ID')
    from google.cloud import secretmanager
    with secretmanager.SecretManagerServiceClient() as secret_client:
        secret = secret_client.access_secret_version(
            request={
                "name": secret_client.secret_version_path(PROJECT_ID, SECRET_ID, "latest")
            }
        )
        return secret.payload.data.decode('UTF-8')

DB_PASS = get_db_pw()



engines = {}
def get_engine(db_name, pool=True):
    """
    Create an engine for creating connection to the SQL database
    Once an engine for a DB was created, it will be reused
    :param db_name: Name of the database to which to connect
    :param pool: set if the engine should use connection pooling
    :return: sqlalchemy engine
    """
    if db_name in engines:
        return engines[db_name]
    else:
        DB_NAME = os.getenv(f'DB_{db_name.upper()}')
        connector = ProxyConnector()
        creator = lambda name : connector.connect(
            INSTANCE_CONNECTION_NAME,
            "pg8000",
            user=DB_USER,
            password=DB_PASS,
            db=DB_NAME
        )
        engine = create_engine(
            "postgresql+pg8000://",
            creator=creator,
            pool_size=30 if pool else 1,
            max_overflow=500 if pool else 10,
            pool_timeout=120,
            pool_recycle=1800
        )
        engines[db_name] = engine
        return engine

def query_df_from_sql(query, db_name, params=None):
    """
    Query a pandas dataframe from a SQL database
    :param query: SQL query string
    :param db_name: name of the DB to query
    :param params: query parameters to be inserted
    :return: pandas dataframe
    """
    engine = get_engine(db_name)
    with engine.connect() as conn:
        res = pd.read_sql_query(query, conn, params=params)
    return res
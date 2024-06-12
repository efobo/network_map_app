#! /usr/bin/python3
import configparser
import psycopg2
from exceptions import *

config_filename = 'config.ini'
cfg = configparser.ConfigParser()
cfg.read(config_filename)
warning_file = cfg['default']['warning_file']
def connect_to_db():
    try:
        db_name = cfg['database']['db_name']
        db_user = cfg['database']['db_username']
        db_password = cfg['database']['db_password']
        db_host = cfg['database']['db_host']
        db_port = cfg['database']['db_port']
        conn = psycopg2.connect(
            dbname=db_name,
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port
        )
        return conn
    except psycopg2.OperationalError as e:
        raise DatabaseConnectionError("Failed to connect to database") from e
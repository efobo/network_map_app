#! /usr/bin/python3
from collect_info2 import collect_info
from check_data import check_data
from db_connection import connect_to_db
import datetime

if __name__ == "__main__":
    start_time = datetime.datetime.now()
    conn = connect_to_db()
    collect_info(conn)
    check_data(conn)
    conn.close()
    end_time = datetime.datetime.now()
    print("Program execution time: " + str(end_time - start_time))
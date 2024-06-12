#! /usr/bin/python3
from db_connection import connect_to_db
from enum import Enum

class WARNING(Enum):
    IFACE_STATE_WARN = 0
    IFACE_DESC_WARN = 1
    ALLOWED_VLANS_WARN = 2
    FINDING_LINKS_WARN = 3

def create_tables(conn):
    cur = conn.cursor()

    cur.execute("drop table if exists devices_table")
    cur.execute("create table devices_table(id serial primary key, hostname text, name text, "
                "mac text, type text, is_root integer default 0, root_iface_desc text)")
    cur.execute("create INDEX devices_idx on devices_table(hostname, name, mac)")
    conn.commit()
    print("devices_table created")

    cur.execute("drop table if exists mac_address_table")
    cur.execute("CREATE TABLE mac_address_table (id serial primary key, hostname text, "
                "mac text, vlan text, iface_name text);")
    cur.execute("create INDEX mac_idx ON mac_address_table(hostname, mac, iface_name);")
    print("mac_address_table created")
    conn.commit()

    cur.execute("drop table if exists links_table")
    cur.execute("create table links_table(id serial primary key, hostname1 text, hostname2 text, mac1 text, mac2 text, "
                "iface1 text, iface2 text)")
    cur.execute("create INDEX links_idx on links_table(hostname1, hostname2, iface1, iface2)")
    conn.commit()
    print("links_table created")

    cur.execute("drop table if exists ifaces_table")
    cur.execute("create table ifaces_table(id serial primary key, name text, "
                "description text, type text, role text, iface_status text, hostname text)")
    cur.execute("create INDEX ifaces_idx on ifaces_table(name, description, hostname, iface_status)")
    conn.commit()
    print("ifaces_table created")

    cur.execute("drop table if exists bonding_table")
    cur.execute("create table bonding_table(id serial primary key, bond_name text, "
                "iface_name text, iface_desc text, iface_status text, hostname text)")
    cur.execute("create INDEX bonding_idx on bonding_table(bond_name, hostname, iface_status)")
    conn.commit()
    print("ports_table created")

    cur.execute("drop table if exists iface_state_warnings_table")
    cur.execute("create table iface_state_warnings_table(id serial primary key, hostname text, "
                "iface_name text, iface_desc text, is_in_agregation integer default 0, warning_text text)")
    conn.commit()
    print("iface_state_warnings_table created")

    cur.execute("drop table if exists iface_desc_warnings_table")
    cur.execute("create table iface_desc_warnings_table(id serial primary key, hostname text, "
                "iface_desc text, device_name_is_empty integer default 0, recommended_iface_desc text, warning_text text)")
    conn.commit()
    print("iface_desc_warnings_table created")

    cur.execute("drop table if exists allowed_vlan_warnings_table")
    cur.execute("create table allowed_vlan_warnings_table(id serial primary key, hostname1 text, "
                "iface1_desc text, hostname2 text, iface2_desc text, warning_text text)")
    conn.commit()
    print("allowed_vlan_warnings_table created")

    cur.execute("drop table if exists warnings_table")
    cur.execute("create table warnings_table(id serial primary key, warning_type integer, "
                "warning_id integer)")
    conn.commit()
    print("warnings_table created")

    cur.execute("drop table if exists finding_links_warnings_table")
    cur.execute("create table finding_links_warnings_table(id serial primary key, hostname1 text, "
                "hostname2 text, iface1 text, warning_text text)")
    conn.commit()
    print("finding_links_warnings_table created")

    print()
    cur.close()


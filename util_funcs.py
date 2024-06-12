#! /usr/bin/python3
import re
from db_connection import connect_to_db
from creds import getcreds
from writer import *
import routeros_api



def contains_ip(input_string):
    ipv4_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
    ipv6_pattern = r'\b(?:[A-Fa-f0-9]{1,4}:){7}[A-Fa-f0-9]{1,4}\b'
    if re.search(ipv4_pattern, input_string):
        return True
    if re.search(ipv6_pattern, input_string):
        return True
    return False

def make_iface_for_match(name1: str, name2: str, iface1: str):
    if name2 == iface1:
        return name1
    numbers = re.findall(r'\d+', iface1)
    last_number = numbers[-1] if numbers else ''
    if last_number == '':
        return name1
    number_str = "-".join(last_number)
    iface_for_match = name1 + "-" + number_str
    return iface_for_match

def is_iface_in_links_table(hostname1: str, hostname2: str, iface2: str, conn):
    cur = conn.cursor()
    cur.execute("SELECT * FROM links_table WHERE hostname1=%(hostname1)s AND hostname2=%(hostname2)s "
                "AND iface2=%(iface2)s", {'hostname1': hostname1, 'hostname2': hostname2, 'iface2': iface2})
    selection = cur.fetchall()
    if len(selection) == 0:
        cur.close()
        return False
    cur.close()
    return True

def is_ifaces_desc_match(name1: str, name2: str, iface1: str, iface2: str):
    iface1_parts = iface1.split('-')
    iface2_parts = iface2.split('-')
    if len(iface1_parts) != len(iface2_parts):
        return False
    if iface1_parts[0] != name2 or iface2_parts[0] != name1:
        return False
    for i in range(len(iface1_parts)):
        if i == 0:
            continue
        if iface1_parts[i] != iface2_parts[i]:
            return False
    return True

def is_this_iface2_in_links_table(hostname1: str, hostname2: str, iface1: str, iface2: str, conn):
    cur = conn.cursor()
    cur.execute("SELECT iface2 FROM links_table WHERE hostname1=%(hostname1)s AND "
                "hostname2=%(hostname2)s AND iface1=%(iface1)s",
                {'hostname1': hostname1, 'hostname2': hostname2, 'iface1': iface1})
    rows = cur.fetchall()
    for row in rows:
        if iface2 == row[0]:
            return True
    return False
def find_iface2_by_desc_match(hostname1: str, hostname2: str, name1: str, name2: str, iface1: str, conn):
    cur = conn.cursor()
    iface2 = make_iface_for_match(name1, name2, iface1)
    print(iface2)
    cur.execute("SELECT name, description FROM ifaces_table WHERE hostname=%(hostname2)s AND "
                "(name=%(iface2)s OR description=%(iface2)s)",
                {'hostname2': hostname2, 'iface2': iface2})
    rows = cur.fetchall()
    if len(rows) == 0:
        cur.close()
        warning = ("there is not enough data in the database for devices " + hostname1 + " and " + hostname2 +
                   " to find the connected interface on device " + hostname2 + ".")
        print("WARNING: " + warning)
        write_to_warning_file("WARNING: " + warning)
        add_finding_links_warn_to_db(hostname1, hostname2, iface1, warning, conn)
        return None
    for row in rows:
        if iface2 == row[0]:
            cur.close()
            return row[0]
        if iface2 == row[1]:
            cur.close()
            return row[1]
    cur.close()
    warning = ("there is not enough data in the database for devices " + hostname1 + " and " + hostname2 +
               " to find the connected interface on device " + hostname2 + ".")
    print("WARNING: " + warning)
    write_to_warning_file("WARNING: " + warning)
    add_finding_links_warn_to_db(hostname1, hostname2, iface1, warning, conn)
    return None

def find_iface2_for_link(mac1: str, mac2: str, hostname1: str, hostname2: str, iface1: str, conn):
    cur = conn.cursor()
    try:
        name1 = ""
        name2 = ""
        cur.execute("SELECT name FROM devices_table WHERE hostname =%(hostname1)s", {'hostname1': hostname1})
        name1 = str(cur.fetchone()[0])
        cur.execute("SELECT name FROM devices_table WHERE hostname =%(hostname2)s", {'hostname2': hostname2})
        name2 = str(cur.fetchone()[0])
        cur.execute("SELECT iface_name FROM mac_address_table WHERE mac = %(mac)s and hostname = %(hostname)s",
                    {'mac': mac1, 'hostname': hostname2})
        selection = cur.fetchall()
        if len(selection) == 0:
            warning = ("to find the connection between the " + hostname1 + " and " + hostname2
                       + " devices via the \"" + iface1 + "\" interface on the " + hostname1 + "device, an analysis of interface descriptions is used.")
            print("WARNING: " + warning)
            write_to_warning_file("WARNING: " + warning)
            cur.close()
            add_finding_links_warn_to_db(hostname1, hostname2, iface1, warning, conn)
            return find_iface2_by_desc_match(hostname1, hostname2, name1, name2, iface1, conn)
        if len(selection) == 1:
            if is_ifaces_desc_match(hostname1, hostname2, iface1, selection[0][0]):
                cur.close()
                return selection[0][0]
            if not is_this_iface2_in_links_table(hostname1, hostname2, iface1, selection[0][0]):
                return selection[0][0]
            warning = ("can't find the interface on the " + hostname2 + " device that is connected to the \"" + iface1
                       + "\" interface of the " + hostname1 + "device.")
            print("WARNING: " + warning)
            write_to_warning_file("WARNING: " + warning)
            cur.close()
            add_finding_links_warn_to_db(hostname1, hostname2, iface1, warning, conn)
            return None
        warning = ("to find the connection between the " + hostname1 +" and " + hostname2
                   + " devices via the \"" + iface1 + "\" interface on the " + hostname1 + " device, an analysis of interface descriptions is used.")
        print("WARNING: " + warning)
        write_to_warning_file("WARNING: " + warning)
        add_finding_links_warn_to_db(hostname1, hostname2, iface1, warning, conn)
        for s in selection:
            if is_ifaces_desc_match(hostname1, hostname2, iface1, s[0]):
                cur.close()
                return s[0]
        return find_iface2_by_desc_match(hostname1, hostname2, name1, name2, iface1, conn)

    except Exception as e:
        print("ERROR: Interface's name search with MACs ", mac1, " and ", mac2, " is failed.")
        print(e)


def find_iface2_for_link_old(mac1: str, mac2: str, hostname1: str, hostname2: str, iface1: str, conn):
    cur = conn.cursor()
    try:
        cur.execute("SELECT iface_name FROM mac_address_table WHERE mac = %(mac)s and hostname = %(hostname)s",
                    {'mac': mac1, 'hostname': hostname2})
        selection = cur.fetchall()
        if len(selection) == 1:
            cur.close()
            return selection[0][0]
        if len(selection) == 0:
            warning = ("there is not enough data in the database for devices " + hostname1 + " and " + hostname2 +
                       " to find the connected interface on device " + hostname2 + ".")
            print("WARNING: " + warning)
            write_to_warning_file("WARNING: " + warning)
            cur.close()
            return ""
        is_diff_iface_name = 0
        first_iface_name = selection[0][0]
        for s in selection:
            if s[0] != first_iface_name:
                is_diff_iface_name = 1
        if is_diff_iface_name == 0:
            cur.close()
            return first_iface_name
        warning = ("there is not enough data in the database for devices " + hostname1 + " and " + hostname2 +
                   " to find the connected interface on device " + hostname2 + ".")
        print("WARNING: " + warning)
        write_to_warning_file("WARNING: " + warning)
        cur.close()
        return ""
    except Exception as e:
        print("ERROR: Interface's name search with MACs ", mac1, " and ", mac2, " is failed.")
        print(e)

def find_hostname_by_mac(mac: str, conn):
    cur = conn.cursor()
    cur.execute("SELECT hostname FROM devices_table WHERE mac=%(mac)s", {'mac': mac})
    result = cur.fetchall()
    cur.close()
    if len(result) > 1:
        print("ERROR: Many devices with 1 mac in devices_table ", mac)
        cur.close()
        return str(result[0][0])
    if len(result) == 0:
        print("ERROR: No devices with this mac ", mac)
        cur.close()
        return None
    cur.close()
    return str(result[0][0])

def find_tagged_vlans_for_iface(hostname: str, iface: str):
    creds = getcreds(hostname)
    connection = routeros_api.RouterOsApiPool(hostname, username=creds['username'], password=creds['password'],
                                              plaintext_login=True)
    connection.socket_timeout = 60.0
    api = connection.get_api()
    vlan_info = api.get_resource('/interface/bridge/vlan')
    tagged_vlans = []
    for v in vlan_info.get():
        vlan_id = v['vlan-ids']
        tagged_ifaces_arr = v['tagged'].split(',')
        if iface in tagged_ifaces_arr:
            tagged_vlans.append(vlan_id)
    connection.disconnect()
    return tagged_vlans


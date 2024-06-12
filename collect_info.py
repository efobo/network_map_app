#! /usr/bin/python3
from initialization import create_tables
from util_funcs import *
import configparser
from db_connection import connect_to_db
from exceptions import *

config_filename = 'config.ini'
cfg = configparser.ConfigParser()
cfg.read(config_filename)

devices_hostnames = set()
devices_macs = set()
devices = {}



def get_info_for_devices_table(hostname: str, api):
    try:
        bridge_info = api.get_resource('/interface/bridge')
        ports_info = api.get_resource('/interface/bridge/port')
        name = api.get_resource('/system/identity').get()[0]['name']
        if not contains_ip(hostname) and name != hostname:
            warning = "WARNING! Hostname ", hostname, " doesn't match with system name ", name
            print(warning)
            with open(warning_file, 'a') as file:
                file.write(warning)
        type = api.get_resource('system/resource').get()[0]['platform']
        local_mac = bridge_info.get()[0]['mac-address']
        root_iface_desc = "false"
        is_root = 1
        for p in ports_info.get():
            if p['role'] == 'root-port':
                root_iface_desc = p['interface']
                is_root = 0
        device = {
            'hostname': hostname,
            'name': name,
            'mac': local_mac,
            'type': type,
            'is_root': is_root,
            'root_iface_desc': root_iface_desc
        }
        return device
    except Exception as e:
        raise RouterOSAPIConnectionError("Failed to connect via RouterOS_API")


def get_info_for_mac_address_table(hostname: str, api):
    macs = api.get_resource('/interface/bridge/host')
    ifaces_info = api.get_resource('/interface')
    interfaces = []
    for m in macs.get(local='false'):
        mac = m['mac-address']
        vlan = m['vid']
        iface_name = m['interface']
        interface_info = {
            'hostname': hostname,
            'mac': mac,
            'vlan': vlan,
            'iface_name': iface_name
        }
        interfaces.append(interface_info)
    return interfaces



def get_info_for_ifaces_table(hostname: str, api):
    ifaces_info = api.get_resource('/interface')
    ports_info = api.get_resource('/interface/bridge/port')
    bonding_info = api.get_resource('/interface/bonding')
    interfaces = []
    checked = []
    for b in bonding_info.get():
        name = b['name']
        checked.append(name)
        type = ifaces_info.get(name=name)[0]['type']
        iface_status = "DOWN"
        if ifaces_info.get(name=name)[0]['running'] == 'true':
            iface_status = "UP"
        elif ifaces_info.get(name=name)[0]['disabled'] == 'true':
            iface_status = "DISABLED"
        role = ""
        if len(ports_info.get(interface=name))>0:
            role = ports_info.get(interface=name)[0]['role']
        for s in str(b['slaves']).split(','):
            checked.append(s)
        interface_info = {
            'name': name,
            'description': "",
            'type': type,
            'role': role,
            'iface_status': iface_status,
            'hostname': hostname
        }
        interfaces.append(interface_info)

    for i in ifaces_info.get():
        if str(i['name']) in checked:
            continue
        name = ""
        description = ""
        if 'default-name' in i:
            name = str(i['default-name'])
            description = str(i['name'])
        else:
            name = str(i['name'])
        type = str(i['type'])
        iface_status = "DOWN"
        if i.get('running') == 'true':
            iface_status = "UP"
        elif i.get('disabled') == 'true':
            iface_status = "DISABLED"
        role = ""
        if len(ports_info.get(interface=description))>0:
            role = ports_info.get(interface=description)[0]['role']
        elif len(ports_info.get(interface=name))>0:
            role = ports_info.get(interface=name)[0]['role']
        interface_info = {
            'name': name,
            'description': description,
            'type': type,
            'role': role,
            'iface_status': iface_status,
            'hostname': hostname
        }
        interfaces.append(interface_info)
    return interfaces

def get_info_for_bonding_table(hostname: str, api):
    ifaces_info = api.get_resource('/interface')
    ports_info = api.get_resource('/interface/bridge/port')
    bonding_info = api.get_resource('/interface/bonding')
    interfaces = []
    for b in bonding_info.get():
        bond_name = b['name']
        for iface_desc in str(b['slaves']).split(','):
            iface_info_cur = ifaces_info.get(name=iface_desc)
            iface_name = iface_info_cur[0]['default-name']
            iface_status = "DOWN"
            if iface_info_cur[0]['running'] == 'true':
                iface_status = "UP"
            elif iface_info_cur[0]['disabled'] == 'true':
                iface_status = "DISABLED"
            interface = {
                'bond_name': bond_name,
                'iface_name': iface_name,
                'iface_desc': iface_desc,
                'iface_status': iface_status,
                'hostname': hostname
            }
            interfaces.append(interface)
    return interfaces

def get_info_for_links_table(hostname: str, conn):
    creds = getcreds(hostname)
    connection = routeros_api.RouterOsApiPool(hostname, username=creds['username'],
                                              password=creds['password'],
                                              plaintext_login=True)
    connection.socket_timeout = 60.0
    api = connection.get_api()
    ports_info = api.get_resource('/interface/bridge/port')
    bridge_info = api.get_resource('/interface/bridge')
    mac1 = bridge_info.get()[0]['mac-address']
    hostname1 = hostname
    links = []
    for p in ports_info.get():
        mac2 = ""
        role = p['role']
        iface1 = p['interface']
        iface2 = ""
        hostname2 = ""
        if role == 'root-port' or role == 'alternate-port':
            designated_bridge = p['designated-bridge']
            mac2 = designated_bridge[-17:]
            hostname2 = find_hostname_by_mac(mac2, conn)
            iface2 = find_iface2_for_link(mac1, mac2, hostname1, hostname2, iface1, conn)
        link = {
            'hostname1': hostname1,
            'hostname2': hostname2,
            'mac1': mac1,
            'mac2': mac2,
            'iface1': iface1,
            'iface2': iface2
        }

        links.append(link)
    connection.disconnect()
    return links

def fill_devices_table(hostname: str, conn, api):
    print("Filling the device_table for ", hostname, " device started.")
    hosts_file = cfg['network']['hosts_file']
    try:
        device = get_info_for_devices_table(hostname, api)
        devices_hostnames.add(device['hostname'])
        devices_macs.add(device['mac'])
        devices[device['hostname']] = {}
        devices[device['hostname']]['name'] = device['name']
        devices[device['hostname']]['mac'] = device['mac']
        devices[device['hostname']]['type'] = device['type']
        devices[device['hostname']]['is_root'] = device['is_root']
        devices[device['hostname']]['root_iface_desc'] = device['root_iface_desc']
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO devices_table (hostname, name, mac, type, is_root, root_iface_desc) "
            "VALUES (%(hostname)s, %(name)s, %(mac)s, %(type)s, %(is_root)s, %(root_iface_desc)s)",
            {'hostname': device["hostname"], 'name': device['name'], 'mac': device["mac"],
             'type': device['type'], 'is_root': device["is_root"], 'root_iface_desc': device["root_iface_desc"]})
        conn.commit()
        print(f"Values:  hostname: {device['hostname']}, name: {device['name']}, mac: {device['mac']}, "
              f"type: {device['type']}, is_root: {device['is_root']}, root_iface_desc: "
              f"{device['root_iface_desc']} INSERTED in devices_table.")
        cur.close()
        return True
    except DatabaseConnectionError as db_error:
        print(f"ERROR: {db_error}")
        return False
    except RouterOSAPIConnectionError as routeros_error:
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO devices_table (hostname) "
                "VALUES (%(hostname)s)",
                {'hostname': hostname})
            conn.commit()
            print(f"Values: hostname: {hostname} INSERTED in devices_table.")
            cur.close()
            return False
        except DatabaseConnectionError as db_error:
            print(f"ERROR: {db_error}")
            return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False
    print("The devices_table for ", hostname, " device is filled in.\n")

def fill_mac_address_table(hostname: str, conn, api):
    print("Filling the mac_address_table for ", hostname, " device started.")
    try:
        mac_adress_table_data = get_info_for_mac_address_table(hostname, api)
        cur = conn.cursor()
        for data in mac_adress_table_data:
            cur.execute("INSERT INTO mac_address_table (hostname, mac, vlan, iface_name) "
                        "VALUES (%(hostname)s, %(mac)s, %(vlan)s, %(iface_name)s)",
                        {'hostname': data['hostname'], 'mac': data['mac'],
                         'vlan': data['vlan'], 'iface_name': data['iface_name']})
            print(f"Values:  hostname: {data['hostname']}, mac: {data['mac']}, vlan: {data['vlan']}, "
                  f"iface_name: {data['iface_name']} INSERTED in mac_address_table.")
            conn.commit()
        cur.close()
    except Exception as e:
        print("ERROR: " + str(e))
    print("The mac_address_table for ", hostname, " device is filled in.\n")

def fill_ifaces_table(hostname: str, conn, api):
    print("Filling the ifaces_table for ", hostname, " device started.")
    iface_info = get_info_for_ifaces_table(hostname, api)
    for data in iface_info:
        cur = conn.cursor()
        cur.execute("INSERT INTO ifaces_table (name, description, type, role, iface_status, hostname) "
                    "VALUES (%(name)s, %(description)s, %(type)s, %(role)s, %(iface_status)s, %(hostname)s)",
                    {'name': data['name'], 'description': data['description'],
                     'type': data['type'], 'role': data['role'], 'iface_status': data['iface_status'],
                     'hostname': data['hostname']})
        conn.commit()
        print(f"Values: name: {data['name']}, description: {data['description']}, type: "
              f"{data['type']}, role: {data['role']}, iface_status: {data['iface_status']}, "
              f"hostname: {data['hostname']} INSERTED in ifaces_table.")
        cur.close()
    print("The ifaces_table for ", hostname, " device is filled in.\n")

def fill_bonding_table(hostname: str, conn, api):
    print("Filling the bonding_table for ", hostname, " device started.")
    bonding_info = get_info_for_bonding_table(hostname, api)
    cur = conn.cursor()
    for data in bonding_info:
        cur.execute("INSERT INTO bonding_table(bond_name, iface_name, iface_desc, iface_status, hostname) "
                    "VALUES (%(bond_name)s, %(iface_name)s, %(iface_desc)s, %(iface_status)s, %(hostname)s)",
                    {'bond_name': data['bond_name'], 'iface_name': data['iface_name'], 'iface_desc': data['iface_desc'],
                     'iface_status': data['iface_status'], 'hostname': data['hostname']})
        conn.commit()
        print(f"Values: bond_name: {data['bond_name']}, iface_name: {data['iface_name']}, iface_desc: "
              f"{data['iface_desc']}, iface_status: {data['iface_status']}, hostname: "
              f"{data['hostname']} INSERTED in bonding_table.")
    cur.close()
    print("The bonding_table for ", hostname, " device is filled in.\n")

def fill_links_table(hostnames, conn):
    print("Filling the links_table started.")
    for hostname in hostnames:
        links = get_info_for_links_table(hostname, conn)
        for link in links:
            if link['mac2'] != "":
                cur = conn.cursor()

                cur.execute("INSERT INTO links_table (hostname1, hostname2, mac1, mac2, iface1, iface2) VALUES (%(hostname1)s, %(hostname2)s, %(mac1)s, %(mac2)s, %(iface1)s, %(iface2)s)",
                            {'hostname1': link['hostname1'], 'hostname2': link['hostname2'], 'mac1': link['mac1'], 'mac2': link['mac2'], 'iface1': link['iface1'], 'iface2': link['iface2']})
                conn.commit()
                print(f"Values: hostname1: {link['hostname1']}, hostname2: {link['hostname2']}, mac1: {link['mac1']}, "
                      f"mac2: {link['mac2']}, iface1: {link['iface1']}, iface2: {link['iface2']} INSERTED in links_table.")
                cur.close()
    print("The links_table is filled in.\n")

def collect_info(conn):
    create_tables(conn)

    hosts_file = cfg['network']['hosts_file']
    with open(hosts_file, 'r') as file:
        for hostname in file:
            try:
                hostname = hostname.replace(' ', '').replace('\n', '')
                creds = getcreds(hostname)
                connection = routeros_api.RouterOsApiPool(hostname, username=creds['username'],
                                                          password=creds['password'],
                                                          plaintext_login=True)
                connection.socket_timeout = 60.0
                api = connection.get_api()
                device_table_result = fill_devices_table(hostname, conn, api)
                if device_table_result:
                    fill_mac_address_table(hostname, conn, api)
                    fill_mac_address_table(hostname, conn, api)
                    fill_ifaces_table(hostname, conn, api)
                    fill_bonding_table(hostname, conn, api)
                connection.disconnect()
            except DatabaseConnectionError as db_error:
                print(f"ERROR: {db_error}")
                continue
            except Exception as e:
                print(f"ERROR: {e}")
                continue
    fill_links_table(devices.keys(), conn)


if __name__ == "__main__":
    conn = connect_to_db()
    collect_info(conn)
    conn.close()

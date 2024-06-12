#! /usr/bin/python3
from db_connection import connect_to_db
from util_funcs import find_tagged_vlans_for_iface
from writer import *


devices = {}

def fill_devices_arr(conn):
    cur = conn.cursor()
    cur.execute("SELECT hostname, name, mac, type, is_root, root_iface_desc FROM devices_table "
                "WHERE name IS NOT NULL AND mac IS NOT NULL AND type IS NOT NULL AND name<>'' AND mac<>'' AND type<>''")
    rows = cur.fetchall()
    for row in rows:
        hostname = row[0]
        name = row[1]
        mac = row[2]
        type = row[3]
        is_root = row[4]
        root_iface_desc = row[5]
        devices[hostname] = {}
        devices[hostname]['name'] = name
        devices[hostname]['mac'] = mac
        devices[hostname]['type'] = type
        devices[hostname]['is_root'] = is_root
        devices[hostname]['root_iface_desc'] = root_iface_desc
    cur.close()


def ifaces_state_check(conn):
    cur = conn.cursor()
    cur.execute("SELECT name, description, type, role, hostname FROM ifaces_table WHERE iface_status='DOWN' "
                "AND (type='bond' OR role='root-port' OR role='designated-port' OR role='alternate-port')")
    conn.commit()
    rows = cur.fetchall()
    for row in rows:
        name = row[0]
        description = row[1]
        type = row[2]
        role = row[3]
        hostname = row[4]
        if type != 'bond':
            warning = ("interface " + name + " with description \"" + description + "\" and role \"" +
                       role + "\" on device " + hostname + " IS DOWN.")
            print("WARNING: " + warning)
            write_to_warning_file("WARNING: " + warning)
            add_iface_state_check_warn_to_db(hostname, name, description, 0, warning, conn)
        else:
            warning = "bond " + name + " on device " + hostname + " IS DOWN."
            print("WARNING: " + warning)
            write_to_warning_file("WARNING: " + warning)

    cur.execute("SELECT bond_name, iface_name, iface_desc, hostname from bonding_table WHERE iface_status='DOWN'")
    conn.commit()
    rows = cur.fetchall()
    for row in rows:
        bond_name = row[0]
        iface_name = row[1]
        iface_desc = row[2]
        hostname = row[3]
        warning = ("interface " + iface_name + " with description \"" + iface_desc + "\" in bond \"" + bond_name +
                   "\" on device " + hostname + " IS DOWN.")
        print("WARNING: " + warning)
        write_to_warning_file("WARNING: " + warning)
        add_iface_state_check_warn_to_db(hostname, iface_name, iface_desc, 1, warning, conn)
    cur.close()


def ifaces_desc_check(conn):
    cur = conn.cursor()
    cur.execute("SELECT hostname1, hostname2, mac1, mac2, iface1, iface2 FROM links_table")
    links = cur.fetchall()
    cur.close()
    for l in links:
        hostname1 = l[0]
        hostname2 = l[1]
        mac1 = l[2]
        mac2 = l[3]
        iface1 = l[4]
        iface2 = l[5]

        try:
            name1 = devices[hostname1]['name']
            name2 = devices[hostname2]['name']
            type1 = devices[hostname1]['type']
            type2 = devices[hostname2]['type']

            if name1 == "" or name2 == "":
                print("WARNING: There is not enough data in the database for MACs ", mac1, " and ", mac2, ".")
                if name1 == "":
                    validation = "name on device ", hostname1, " is empty."
                    print("WARNING: " + validation)
                    write_to_warning_file("WARNING: " + validation)
                    add_iface_desc_check_warn_to_db(hostname1, iface1, 1, "", validation, conn)
                if name2 == "":
                    validation = "name on device ", hostname2, "is empty."
                    print("WARNING: " + validation)
                    write_to_warning_file("WARNING: " + validation)
                    add_iface_desc_check_warn_to_db(hostname2, iface2, 1, "", validation, conn)
                continue
            if not (name2 in iface1):
                validation = ("bad description for interface ", iface1, " on device ", hostname1,
                              " recommended description is \"", name2, "\".")
                print("VALIDATION: " + validation)
                write_to_warning_file("VALIDATION: " + validation)
                add_iface_desc_check_warn_to_db(hostname1, iface1, 0, name2, validation, conn)
            if not (name1 in iface2):
                validation = "bad description for interface ", iface2, " on device ", hostname2, " recommended description is \"", name1, "\"."
                print("VALIDATION: " + validation)
                write_to_warning_file("VALIDATION: " + validation)
                add_iface_desc_check_warn_to_db(hostname2, iface2, 0, name1, validation, conn)
            if (name2 in iface1) and (name1 in iface2):
                print("Interface's descriptions ", iface1, " and ", iface2, " between ", hostname1,
                      " and ", hostname2, " is Ok.")
        except Exception as e:
            print("ERROR: Interface's descriptions check for devices ", hostname1, " and ", hostname2,
                  " with interfaces ", iface1, " and ", iface2, " is failed.")
            print(e)


def vlan_check(conn):
    cur = conn.cursor()
    cur.execute("SELECT hostname1, hostname2, mac1, mac2, iface1, iface2 FROM links_table")
    rows = cur.fetchall()
    cur.close()
    for row in rows:
        hostname1 = row[0]
        hostname2 = row[1]
        mac1 = row[2]
        mac2 = row[3]
        iface1 = row[4]
        iface2 = row[5]
        if hostname2 == "" or iface2 == "":
            if mac2 != "":
                warning = ("connection to an unknown device with mac " + mac2 + " was detected on the \"" +
                           iface1 +"\" interface on the " + hostname1 + " device.")
                print("WARNING: " + warning)
                write_to_warning_file("WARNING: " + warning)
                add_vlan_check_warn_to_db(hostname1, iface1, hostname2, iface2, warning, conn)
                return
            else:
                warning = ("connection to an unknown device was detected on the \"" +
                           iface1 +"\" interface on the " + hostname1 + " device.")
                print("WARNING: " + warning)
                write_to_warning_file("WARNING: " + warning)
                add_vlan_check_warn_to_db(hostname1, iface1, hostname2, iface2, warning, conn)
        tagged_vlans1 = find_tagged_vlans_for_iface(hostname1, iface1)
        tagged_vlans2 = find_tagged_vlans_for_iface(hostname2, iface2)
        is_correct = 1
        if len(tagged_vlans1) != len(tagged_vlans2):
            validation = ("interface \"" + iface1 + "\" on " + hostname1 + " device and interface \"" +
                          iface2 + "\" on " + hostname2 + " devices has different number of allowed VLANs.")
            print("VALIDATION: " + validation)
            write_to_warning_file("VALIDATION: " + validation)
            add_vlan_check_warn_to_db(hostname1, iface1, hostname2, iface2, validation, conn)

        else:
            for tv1 in tagged_vlans1:
                if not tv1 in tagged_vlans2:
                    is_correct = 0
                    validation = ("interface \"" + iface1 + "\" on " + hostname1 + " device and interface \"" +
                                  iface2 + "\" on " + hostname2 + " devices has different allowed VLANs.")
                    print("VALIDATION: " + validation)
                    write_to_warning_file("VALIDATION: " + validation)
                    add_vlan_check_warn_to_db(hostname1, iface1, hostname2, iface2, validation, conn)
        if is_correct == 1:
            print("The checking of the allowed VLANs on interface \"", iface1, "\" on device ", hostname1, " and on interface \"", iface2,
                  "\" on device ", hostname2, " was successful.")

def check_data(conn):
    fill_devices_arr(conn)
    ifaces_state_check(conn)
    ifaces_desc_check(conn)
    vlan_check(conn)

if __name__ == "__main__":
    conn = connect_to_db()
    check_data(conn)
    conn.close()
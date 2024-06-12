import configparser
from initialization import WARNING

config_filename = 'config.ini'
cfg = configparser.ConfigParser()
cfg.read(config_filename)
warning_file = cfg['default']['warning_file']

with open(warning_file, 'r+') as file:
    file.seek(0)
    file.truncate()

def write_to_warning_file(warning_text: str):
    with open(warning_file, 'a') as file:
        file.write(warning_text + '\n')

def add_iface_state_check_warn_to_db(hostname: str, iface_name: str, iface_desc: str,
                                     is_in_agregation: int, warning_text: str, conn):
    cur = conn.cursor()
    cur.execute("INSERT INTO iface_state_warnings_table (hostname, iface_name, iface_desc, "
                "is_in_agregation, warning_text) VALUES (%(hostname)s, %(iface_name)s, "
                "%(iface_desc)s, %(is_in_agregation)s, %(warning_text)s) RETURNING id",
                {'hostname': hostname, 'iface_name': iface_name, 'iface_desc': iface_desc,
                 'is_in_agregation': is_in_agregation, 'warning_text': warning_text})
    conn.commit()
    warn_id = cur.fetchone()
    cur.execute("INSERT INTO warnings_table (warning_type, warning_id) "
                "VALUES (%(warning_type)s, %(warning_id)s)",
                {'warning_type': WARNING.IFACE_STATE_WARN.value, 'warning_id': warn_id})
    conn.commit()
    cur.close()

def add_iface_desc_check_warn_to_db(hostname: str, iface_desc: str, device_name_is_empty: int,
                                    recommended_iface_desc: str, warning_text: str, conn):
    cur = conn.cursor()
    cur.execute("INSERT INTO iface_desc_warnings_table (hostname, iface_desc, "
                            "device_name_is_empty, recommended_iface_desc, warning_text) "
                            "VALUES (%(hostname)s, %(iface_desc)s, %(device_name_is_empty)s, "
                            "%(recommended_iface_desc)s, %(warning_text)s) RETURNING id",
                            {'hostname': hostname, 'iface_desc': iface_desc, 'device_name_is_empty': device_name_is_empty,
                             'recommended_iface_desc': recommended_iface_desc,  'warning_text': warning_text})
    conn.commit()

    warn_id = cur.fetchone()

    cur.execute("INSERT INTO warnings_table (warning_type, warning_id) "
                "VALUES (%(warning_type)s, %(warning_id)s)",
                {'warning_type': WARNING.IFACE_DESC_WARN.value, 'warning_id': warn_id})
    conn.commit()
    cur.close()

def add_vlan_check_warn_to_db(hostname1: str, iface1_desc: str, hostname2: str, iface2_desc: str, warning_text: str, conn):
    cur = conn.cursor()
    cur.execute("INSERT INTO allowed_vlan_warnings_table (hostname1, iface1_desc, "
                "hostname2, iface2_desc, warning_text) "
                "VALUES (%(hostname1)s, %(iface1_desc)s, %(hostname2)s, "
                "%(iface2_desc)s, %(warning_text)s) RETURNING id",
                {'hostname1': hostname1, 'iface1_desc': iface1_desc, 'hostname2': hostname2,
                 'iface2_desc': iface2_desc, 'warning_text': warning_text})
    conn.commit()
    warn_id = cur.fetchone()
    cur.execute("INSERT INTO warnings_table (warning_type, warning_id) "
                "VALUES (%(warning_type)s, %(warning_id)s)",
                {'warning_type': WARNING.ALLOWED_VLANS_WARN.value, 'warning_id': warn_id})
    conn.commit()
    cur.close()

def add_finding_links_warn_to_db(hostname1: str, hostname2: str, iface1: str, warning_text: str, conn):
    cur = conn.cursor()
    cur.execute("INSERT INTO finding_links_warnings_table (hostname1, hostname2, iface1, warning_text) "
                "VALUES (%(hostname1)s, %(hostname2)s, %(iface1)s, "
                "%(warning_text)s) RETURNING id",
                {'hostname1': hostname1, 'hostname2': hostname2, 'iface1': iface1,
                 'warning_text': warning_text})
    conn.commit()
    warn_id = cur.fetchone()[0]
    cur.execute("INSERT INTO warnings_table (warning_type, warning_id) "
                "VALUES (%(warning_type)s, %(warning_id)s)",
                {'warning_type': WARNING.FINDING_LINKS_WARN.value, 'warning_id': warn_id})
    conn.commit()
    cur.close()
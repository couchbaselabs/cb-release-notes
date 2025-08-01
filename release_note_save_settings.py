
import sqlite3


def load_database(database_file: str):
    conn = sqlite3.connect(database_file)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS saved_settings 
                 (release_module TEXT, 
                  module_field TEXT,
                  field_value TEXT,
                  PRIMARY KEY(release_module, module_field)
                 )
              ''')
    conn.commit()
    return conn

def save_item(conn, release_module, module_field, field_value):
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE 
                 INTO saved_settings VALUES (?,?,?)
              ''', 
              (release_module, module_field, field_value))
    conn.commit()
    
def get_saved_items(conn, release_module, module_field):
    c = conn.cursor()
    c.execute('''SELECT field_value
                 FROM saved_settings
                 WHERE release_module = ?
                   AND module_field = ?''',
              (release_module, module_field))
    result = c.fetchone()
    return result[0] if result else ''

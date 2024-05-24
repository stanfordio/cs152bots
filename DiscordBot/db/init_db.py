import sqlite3
import sys

# Function to execute SQL scripts from a file


def execute_scripts_from_file(filename, connection):
    with open(filename, 'r') as fd:
        sql_file = fd.read()

    sql_commands = sql_file.split(';')
    cursor = connection.cursor()
    for command in sql_commands:
        try:
            if command.strip():
                cursor.execute(command)
        except Exception as error:
            print(f"Error executing SQL: {error}")
            connection.rollback()
            cursor.close()
            return 1
    cursor.close()
    connection.commit()


def main():
    try:
        conn = sqlite3.connect('mod_db.sqlite')
        execute_scripts_from_file("db/schema.sql", conn)
        execute_scripts_from_file("db/seeders.sql", conn)
    except Exception as error:
        print(f"Error: {error}")
        sys.exit(1)
    finally:
        if conn:
            conn.close()


if __name__ == '__main__':
    main()

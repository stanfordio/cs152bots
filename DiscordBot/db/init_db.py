import sqlite3
import sys


# Function to execute SQL scripts from a file
def execute_scripts_from_file(filename, connection):
    # Open and read the file as a single buffer
    with open(filename, 'r') as fd:
        sql_file = fd.read()

    # Execute every command from the input file
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
        # Connect to the database and execute the SQL scripts
        conn = sqlite3.connect('mod_db.sqlite')
        # Create the database schema
        execute_scripts_from_file("db/schema.sql", conn)
        # Seed the database with initial data
        execute_scripts_from_file("db/seeders.sql", conn)

    except Exception as error:
        print(f"Error: {error}")
        sys.exit(1)
    finally:
        if conn:
            conn.close()


if __name__ == '__main__':
    main()

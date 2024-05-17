## Database Setup with SQLite

To initialize the SQLite database, follow these steps:

1. Ensure Python is installed on your system.
2. Run the following command from the root directory of the project:

python db/init_db.py

This will create a SQLite database named `myprojectdb.sqlite` in your project directory and populate it with initial data.

To access the database, you can use the `sqlite3` command-line utility or a GUI tool like DB Browser for SQLite.

For more information on SQLite, see the [official documentation](https://www.sqlite.org/docs.html).

## Database Schema

The database schema consists of the following tables:

1. `users`: Contains information about registered users.
2. `reports`: Contains information about moderation reports.
3. `messages`: Contains information about messages reported by users
4. `user_history`: Contains information about user reporting history
5. `moderation_history`: Contains information about moderation actions taken by moderators

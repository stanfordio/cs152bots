## Database Setup with SQLite

To initialize the SQLite database run:

python db/init_db.py

To access the database, you can use the `sqlite3` command-line utility or a GUI tool like DB Browser for SQLite.

For more information on SQLite, see the [official documentation](https://www.sqlite.org/docs.html).

## Database Schema

The database schema consists of the following tables:

1. `users`: Contains information about registered users.
2. `reports`: Contains information about moderation reports.
3. `messages`: Contains information about messages reported by users
4. `user_history`: Contains information about user reporting history
5. `moderation_history`: Contains information about moderation actions taken by moderators

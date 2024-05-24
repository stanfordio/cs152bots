DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS reports;
DROP TABLE IF EXISTS messages;
DROP TABLE IF EXISTS user_history;
DROP TABLE IF EXISTS moderation_history;

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reports (
    report_id INTEGER PRIMARY KEY AUTOINCREMENT,
    reported_user_id INTEGER,
    reporter_user_id INTEGER,
    reportee TEXT,
    reported_user TEXT,
    reported_message TEXT,
    report_category TEXT,
    report_subcategory TEXT,
    additional_details TEXT,
    priority INTEGER,
    report_status TEXT DEFAULT 'pending',
    time_reported TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (reported_user_id) REFERENCES users (user_id),
    FOREIGN KEY (reporter_user_id) REFERENCES users (user_id)
);

CREATE TABLE IF NOT EXISTS messages (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    channel_id TEXT,
    FOREIGN KEY (user_id) REFERENCES users (user_id)
);

CREATE TABLE IF NOT EXISTS user_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,
    action_details TEXT,
    action_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (user_id)
);

CREATE TABLE IF NOT EXISTS moderation_history (
    mod_history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    moderator_user_id INTEGER,
    affected_user_id INTEGER,
    action_taken TEXT NOT NULL,
    action_details TEXT,
    action_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (moderator_user_id) REFERENCES users (user_id),
    FOREIGN KEY (affected_user_id) REFERENCES users (user_id)
);

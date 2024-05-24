INSERT INTO users
    (username, status)
VALUES
    ('alice', 'active'),
    ('bob', 'banned');

INSERT INTO reports
    (reported_user_id, reporter_user_id, reportee, reported_user, reported_message, report_category, report_subcategory, additional_details, priority, report_status)
VALUES
    (
        (SELECT user_id
        FROM users
        WHERE username='alice'),
        (SELECT user_id
        FROM users
        WHERE username='bob'),
        'bob',
        'alice',
        'User Alice was verbally abusive.',
        'harassment',
        'verbal abuse',
        NULL,
        1,
        'pending'
    );

INSERT INTO messages
    (user_id, content, channel_id)
VALUES
    (
        (SELECT user_id
        FROM users
        WHERE username='alice'),
        'Hello there!',
        'general'
    );

INSERT INTO user_history
    (user_id, action, action_details)
VALUES
    (
        (SELECT user_id
        FROM users
        WHERE username='bob'),
        'login',
        'User Bob logged in from IP 192.168.1.1.'
    );

INSERT INTO moderation_history
    (moderator_user_id, affected_user_id, action_taken, action_details)
VALUES
    (
        (SELECT user_id
        FROM users
        WHERE username='bob'),
        (SELECT user_id
        FROM users
        WHERE username='alice'),
        'warning issued',
        'Bob issued a warning to Alice for inappropriate behavior.'
    );

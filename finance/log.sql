CREATE TABLE transactions (
                            user_id INTEGER NOT NULL,
                            symbol TEXT NOT NULL,
                            shares INTEGER, price REAL,
                            cash_before REAL,
                            cash_spent REAL,
                            cash_after REAL,
                            date_time DATETIME,
                            FOREIGN KEY(user_id) REFERENCES users(id));

INSERT INTO transactions (user_id, symbol, shares, date_time) VALUES (99, 'aal', 5, '2023-01-01 10:10:10');

CREATE TABLE transactions (user_id INTEGER NOT NULL, symbol TEXT NOT NULL, shares INTEGER, price REAL, cash_before REAL, cash_spent REAL, cash_after REAL,'date_time' DATETIME, FOREIGN KEY(user_id) REFERENCES users(id));

CREATE TABLE portfolios ('user_id' INTEGER NOT NULL, 'symbol' TEXT NOT NULL UNIQUE, 'shares' INTEGER, 'value' REAL, FOREIGN KEY(user_id) REFERENCES users(id));
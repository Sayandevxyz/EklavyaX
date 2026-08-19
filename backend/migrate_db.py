import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "eklavyax.db")
con = sqlite3.connect(db_path)
cur = con.cursor()

cols = [c[1] for c in cur.execute("PRAGMA table_info(users)").fetchall()]
if "gender" not in cols:
    cur.execute("ALTER TABLE users ADD COLUMN gender VARCHAR(20)")
    print("Added gender column to users table.")
else:
    print("gender column already exists.")

cur.execute("UPDATE users SET gender = 'boy', avatar_url = 'assets/img/student_boy.jpg' WHERE username IN ('sayan-mondal', 'rishabh-raj')")
con.commit()

print("Current users:")
for row in cur.execute("SELECT id, username, role, gender, avatar_url FROM users").fetchall():
    print(row)

con.close()

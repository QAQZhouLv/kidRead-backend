import sqlite3

DB_PATH = "kidread.db"

SQLS = [
    "ALTER TABLE stories ADD COLUMN is_favorite BOOLEAN NOT NULL DEFAULT 0;",
    "ALTER TABLE stories ADD COLUMN is_deleted BOOLEAN NOT NULL DEFAULT 0;",
    "ALTER TABLE stories ADD COLUMN deleted_at DATETIME;"
]

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for sql in SQLS:
        try:
            print("Executing:", sql)
            cursor.execute(sql)
        except Exception as e:
            print("Skip / Error:", e)

    conn.commit()
    conn.close()
    print("Done.")

if __name__ == "__main__":
    main()
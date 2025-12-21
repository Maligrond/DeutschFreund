
import sqlite3
import os

DB_PATH = "backend/data/germanbuddy.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if columns exist
        cursor.execute("PRAGMA table_info(vocabulary)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "next_review" not in columns:
            print("Adding next_review column...")
            cursor.execute("ALTER TABLE vocabulary ADD COLUMN next_review TIMESTAMP")
            # Set default to now
            cursor.execute("UPDATE vocabulary SET next_review = datetime('now')")
            
        if "interval" not in columns:
            print("Adding interval column...")
            cursor.execute("ALTER TABLE vocabulary ADD COLUMN interval FLOAT DEFAULT 0.0")
            
        if "ease_factor" not in columns:
            print("Adding ease_factor column...")
            cursor.execute("ALTER TABLE vocabulary ADD COLUMN ease_factor FLOAT DEFAULT 2.5")
            
        conn.commit()
        print("Migration completed successfully!")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()

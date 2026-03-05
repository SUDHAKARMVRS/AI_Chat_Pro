import psycopg2

conn = psycopg2.connect(
    dbname="postgres",
    user="postgres",
    password="Nadhi@2508",
    host="localhost",
    port="5432"
)

cur = conn.cursor()

# Insert sample user
cur.execute(
    "INSERT INTO users (username, password) VALUES (%s, %s)",
    ("sukar", "hashed_password")
)

conn.commit()

print("User inserted successfully!")

conn.close()
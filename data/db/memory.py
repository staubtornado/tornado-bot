from sqlite3 import connect, Connection

database: Connection = connect(":memory:")

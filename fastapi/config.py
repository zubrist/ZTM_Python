"""
Database configuration for Tortoise ORM
"""

import os
from pathlib import Path

# Get the project root directory
BASE_DIR = Path(__file__).resolve().parent
'''
BASE_DIR = Path(__file__).resolve().parent
explanation:
- `__file__`: This is a special variable in Python that contains the path to
    the current file (in this case, `config.py`).
    
- .resolve(): This method resolves the path to an absolute path,
    which means it will convert any relative path to an absolute one.
    This is useful to ensure that we have a consistent path regardless 
    of where the script is run from.
    
- .parent: This attribute gives us the parent directory of the current file.
    Since `config.py` is located in the `fastapi` directory, 
    `BASE_DIR` will point to the `fastapi` directory itself, 
    which is the root of our project.    
    

'''

# SQLite database path
DB_PATH = BASE_DIR / "db" / "app.db"

# Tortoise ORM configuration
TORTOISE_ORM = {
    "connections": {
        "default": {
            "engine": "tortoise.backends.sqlite",
            "credentials": {
                "file_path": str(DB_PATH),
                "journal_mode": "wal",  # Write-Ahead Logging for better concurrency
            }
        }
    },
    "apps": {
        "models": {
            "models": ["models"],  # Import models from models.py
            "default_connection": "default",
        }
    },
}
'''

whats happening here in TORTOISE_ORM congiguration:
- "connections": This section defines the database connections.
We have a single connection named "default" that uses the SQLite engine 
provided by Tortoise ORM. 
The credentials specify the file path to the SQLite database and set 
the journal mode to "wal" for better performance.

-journal_mode: This is a SQLite configuration that enables Write-Ahead Logging (WAL).
WAL allows for better concurrency and performance when multiple processes or threads are accessing the database.

for example, if you have multiple requests hitting your FastAPI application
that need to read/write to the database, WAL can help improve performance
by allowing concurrent reads and writes without locking the entire database.
'''


'''
- "apps": This section defines the applications and their associated models.
We have a single app named "models" that imports the models from the 
`models.py`


'''


# Database URL (for reference)
DATABASE_URL = f"sqlite://{DB_PATH}"

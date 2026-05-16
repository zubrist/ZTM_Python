# pydantic modeks for validating data in FastAPI

"""
Tortoise ORM Models - Database Schema Definition

KEY INTERVIEW QUESTION:
"What's the difference between Tortoise ORM models and Pydantic schemas?"
Answer: ORM models = database tables. Pydantic schemas = API validation.
They're completely separate! ORM doesn't validate, Pydantic doesn't touch DB.
"""

from fastapi import FastAPI
from pydantic import BaseModel


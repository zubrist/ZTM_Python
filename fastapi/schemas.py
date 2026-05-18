# request/response schemas for FastAPI

"""
Pydantic Schemas - Request/Response Validation

INTERVIEW QUESTION: "What's the difference between Tortoise ORM models and Pydantic schemas?"
ANSWER: 
- ORM models = Database structure (tables, columns)
- Pydantic schemas = API validation (request/response data)

Why separate?
1. You might want to hide some DB fields from API (like password_hash)
2. You might want to validate user input before storing
3. Same database can be used by multiple APIs

Example:
- ORM: User.password_hash (stored in DB, 60+ chars, hashed)
- API response: Never send password_hash to client!
- Pydantic schema: Has 'password' (for input), not 'password_hash'
"""

from pydantic import BaseModel, Field , EmailStr, field_validator
from typing import Optional
from datetime import datetime , date
import re


# ============ TODO SCHEMAS ============

class TodoCreate(BaseModel):
    """
    Schema for CREATING a todo
    This is what the client sends in POST request body
    """
    title: str = Field(..., min_length=1, max_length=200, example="Buy groceries")
    
    """
    Field(...): The ellipsis (...) means this field is REQUIRED
    
    - min_length=1: Title must be at least 1 character (can't be empty)
    - max_length=200: Title can't exceed 200 characters
    - example="Buy groceries": Shows example in Swagger UI
    
    Without Field():
    class TodoCreate(BaseModel):
        title: str  # This works too! But no constraints
        
    But with Field(), you can add constraints:
    - min_length, max_length: For strings
    - gt, lt, ge, le: For numbers (greater than, less than, etc)
    - regex: For pattern matching
    - description: For API documentation
    
    PYDANTIC VALIDATION HAPPENS AUTOMATICALLY:
    If user sends: {"title": ""} → Error! min_length violation
    If user sends: {"title": "Buy"} → OK! Valid
    If user sends: {"title": "x" * 300} → Error! max_length violation
    """
    
    description: Optional[str] = Field(None, max_length=500, example="Milk, Bread, Eggs")
    """
    Optional[str] = Field(None, ...):
    - Optional[str]: This field can be either str or None
    - = None: Default value is None (not provided = None)
    - Max_length=500: If provided, can't exceed 500 chars
    
    User can send:
    {"title": "Buy", "description": "Milk, bread"} → OK, description is set
    {"title": "Buy"} → OK, description=None
    {"title": "Buy", "description": null} → OK, same as above
    """


class TodoUpdate(BaseModel):
    """
    Schema for UPDATING a todo (PATCH request)
    All fields optional for partial updates
    
    INTERVIEW QUESTION: "How do you handle partial updates in REST APIs?"
    ANSWER: Make all fields optional in the update schema
    """
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    completed: Optional[bool] = None
    
    @field_validator('title')
    @classmethod
    def title_no_special_chars(cls, v: str) -> str:
        """
        @field_validator('title'): This runs BEFORE Pydantic saves the field
        
        WHAT IT DOES:
        - Receives the raw title value from the request
        - Checks if it contains special characters
        - Returns cleaned value if valid, or raises error if invalid
        
        WHEN IT RUNS:
        User sends PUT request → Pydantic receives title → Validator runs → ✓ Saved or ✗ Error
        
        SPECIAL CHARACTERS BLOCKED:
        !@#$%^&*()_+-={}[]|:;<>?,./\~`
        """
        
        # Only validate if title is actually provided (could be None for PATCH)
        if v is None:
            return v
        
        # Pattern: any character that is NOT alphanumeric, spaces, or hyphens
        # Allows: letters, numbers, spaces, hyphens
        # Blocks: !@#$%^&*()_+={}[]|:;<>?,./\~`
        special_chars_pattern = r'[^a-zA-Z0-9\s\-]'
        
        if re.search(special_chars_pattern, v):
            # Extract which special characters were found (for better error message)
            found_chars = set(re.findall(r'[^a-zA-Z0-9\s\-]', v))
            raise ValueError(
                f"Title contains invalid characters: {', '.join(sorted(found_chars))}. "
                f"Only letters, numbers, spaces, and hyphens are allowed."
            )
        
        return v  # Return the validated (and unchanged) value


class TodoResponse(BaseModel):
    """
    Schema for RETURNING a todo in responses
    This is what you send back to the client
    
    INTERVIEW QUESTION: "Why use a separate response schema?"
    ANSWER: You might fetch more data from DB than you want to send to client
    Example: Don't send internal timestamps or secret fields
    """
    id: int
    title: str
    description: Optional[str]
    completed: bool
    created_at: datetime  # Pydantic auto-converts to ISO format in JSON
    
    class Config:
        from_attributes = True  # ← PYDANTIC V2 SYNTAX (was orm_mode=True in V1)
    
    """
    from_attributes = True: This tells Pydantic how to convert ORM models to schemas
    
    WITHOUT this:
    todo = await Todo.get(id=1)  # Tortoise ORM object
    return TodoResponse(todo)  # ❌ Error! Pydantic doesn't know how to read ORM attributes
    
    WITH this:
    todo = await Todo.get(id=1)  # Tortoise ORM object
    return TodoResponse.from_orm(todo)  # ✅ Works! Pydantic reads todo.id, todo.title, etc
    
    Actually in FastAPI, you can just:
    return todo  # ✅ FastAPI automatically calls from_orm() because response_model is set
    
    HOW IT WORKS:
    ORM object: todo = Todo(id=1, title="Buy milk", created_at=datetime(...))
    Pydantic reads: todo.id, todo.title, todo.created_at using getattr()
    Validates: Ensures they match the schema types
    Converts: Serializes to JSON for API response
    """


# ============ USER SCHEMAS ============

class UserCreate(BaseModel):
    """Schema for creating a user"""
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr = Field(..., description="User email address")
    dob : date = Field(None, description="user`s date of birth")


class UserResponse(BaseModel):
    """Schema for returning a user"""
    id: int
    name: str
    email: str
    dob: date
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============ PRODUCT SCHEMAS ============

class ProductCreate(BaseModel):
    """Schema for creating a product"""
    name: str = Field(..., min_length=1, max_length=200)
    price: float = Field(..., gt=0, description="Price must be greater than 0")
    """
    gt=0: "greater than 0"
    This means price > 0 (can't be 0 or negative)
    
    Other numeric constraints:
    - gt: greater than
    - lt: less than
    - ge: greater than or equal
    - le: less than or equal
    
    Example: age: int = Field(..., ge=0, le=150)
    This means age must be between 0 and 150
    """
    description: Optional[str] = None


class ProductUpdate(BaseModel):
    """Schema for updating a product"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    price: Optional[float] = Field(None, gt=0)
    description: Optional[str] = None


class ProductResponse(BaseModel):
    """Schema for returning a product"""
    id: int
    name: str
    price: float
    description: Optional[str]
    in_stock: bool
    created_at: datetime
    
    class Config:
        from_attributes = True





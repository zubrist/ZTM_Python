# pydantic modeks for validating data in FastAPI

"""
Tortoise ORM Models - Database Schema Definition

KEY INTERVIEW QUESTION:
"What's the difference between Tortoise ORM models and Pydantic schemas?"
Answer: ORM models = database tables. Pydantic schemas = API validation.
They're completely separate! ORM doesn't validate, Pydantic doesn't touch DB.
"""

from tortoise import fields
from tortoise.models import Model



class Todo(Model):
    """
    A TODO item model
    
    When you create a Todo model, Tortoise automatically:
    1. Creates a "todo" table in SQLite
    2. Creates columns for each field
    3. Handles auto-increment for id
    
    QUESTION: "How does Tortoise ORM map Python classes to database tables?"
    Answer: Each Model class = one table. Each field = one column.
    """
    
    id = fields.IntField(pk=True)  # Primary key, auto-incrementing
    title = fields.CharField(max_length=255)  # Title of the TODO item
    '''
    Charfield - VARCHAR in Db || max_lenght=200 means VARCHAR(200)
    
    '''
    description = fields.TextField(null = True)  # Detailed description of the TODO item
    '''
    TextField - TEXT in Db ( no sizelimit)
    null=True means this field can be empty (optional)
    '''
    
    completed = fields.BooleanField(default=False)  # Status of the TODO item (completed or not)
    '''
    BooleanFeild - BOOLEAN/TINYINT ib Db 
    default=False means default value is False (not completed)
    
    What happens if I don't set default=False?
    if we don't set default, then completed will be required when creating a new Todo item.
    This means you would have to explicitly provide a value for completed every time you create a new
    Todo item, which can be inconvenient. Setting default=False allows you to create a new Todo item without
    specifying the completed status, and it will automatically be set to False (not completed) by default.
    
     
    '''
    
    created_at = fields.DatetimeField(auto_now_add=True)  # Timestamp when the TODO item was created
    '''
    auto_now_add=True means this field is automatically set to 
    the current date and time when a new record is created ,
    never changed after that
    
    Question: When Would you use auto_now_add vs auto_now in Tortoise ORM?
    Answer: auto_now_add for created_at (set once on creation),
    auto_now for updated_at (update every time record is saved)
    
    '''
    
    updated_at = fields.DatetimeField(auto_now=True)  # Timestamp when the TODO item was last updated
    
    class Meta:  # ✅ IMPORTANT: Must be uppercase "Meta", not "meta"!
        table = "todo"  # Specify the table name in the database
        '''
        By default, Tortoise ORM would create a table named "todo" based on the class name.
        However, we can explicitly specify the table name using the Meta class. 
        This is useful for clarity and to ensure the table name is exactly what we want.
        
        INTERVIEW TIP: This is a common mistake! Meta class MUST be uppercase.
        If you write "class meta:", Tortoise won't recognize it and model registration fails.
        '''
        
    def __str__(self):
        return f"Todo(id={self.id}, title='{self.title}', completed={self.completed})"
    
    '''
    this is a string representation of the model instance, which is helpful for debugging and logging.
    When you print a Todo instance, it will show the id, title, and completed status in a readable format.
    

    '''
        
         
class Users(Model):
    id = fields.IntField(pk = True)
    name = fields.CharField(max_length = 50)
    email = fields.CharField(max_length = 100, unique = True)
    dob = fields.DateField(null= True)
    created_at = fields.DatetimeField(auto_now_add= True)
    updated_at = fields.DatetimeField(auto_now= True)
    
    class Meta:
        table = "users"
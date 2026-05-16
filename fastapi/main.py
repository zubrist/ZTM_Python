# this is my main FastAPI application file


from fastapi import FastAPI


app = FastAPI()


@app.get("/")
async def hello():
    return{'data':'hello world'}


@app.get("/about")
async def about():
    return {'data':'this is the content of about page'}
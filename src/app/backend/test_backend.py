from fastapi import FastAPI

app = FastAPI()

@app.get("/items")
async def get_item(skip: int, limit: int | None = None):
    return {"Get items with": {"skip": skip, "limit": limit}}
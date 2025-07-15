from fastapi import FastAPI
from config.config import settings

print(settings.DATABASE_URL)

app = FastAPI(title="Syncline")

@app.get("/")
def root():
    return {"message": "Syncline AI is running"}
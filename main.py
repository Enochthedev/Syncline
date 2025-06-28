from fastapi import FastAPI
from config.config import settings

print(settings.DATABASE_URL)

app = FastAPI(title="AI Communication Agent")

@app.get("/")
def root():
    return {"message": "AI Communication Agent is running"}
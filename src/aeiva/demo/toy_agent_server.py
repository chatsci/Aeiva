# server.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Enable CORS for all origins (for development purposes)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins; adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define the request model
class MessageRequest(BaseModel):
    message: str

# Define the response model
class MessageResponse(BaseModel):
    response: str

@app.post("/process_text", response_model=MessageResponse)
async def process_text(request: MessageRequest):
    if not request.message:
        raise HTTPException(status_code=400, detail="No message provided")
    
    print(f"Received message from Unity: {request.message}")
    
    # Toy agent logic: Always respond with "yes"
    response_text = "yes"
    
    return MessageResponse(response=response_text)
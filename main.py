from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
import logging

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Wohoo! Media Engine is running!"}

class ImageGenerationPayload(BaseModel):
    callback: str
    workflow_input: dict

class VideoGenerationPayload(BaseModel):
    callback: str
    workflow_input: dict

latest_webhook_response = None

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.post("/image-generation", response_model=dict)
async def generate_image(payload: ImageGenerationPayload):
    url = "https://salt-api-prod.getsalt.ai/api/v1/deployments/402a0423-e8d0-4eee-9022-0b12444c4400/executions/"
    headers = {
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload.dict(), headers=headers)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    

@app.post("/video-generation", response_model=dict)
async def generate_video(payload: VideoGenerationPayload):
    url = "https://salt-api-prod.getsalt.ai/api/v1/deployments/402a0423-e8d0-4eee-9022-0b12444c4400/executions/"
    headers = {
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload.dict(), headers=headers)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


@app.post("/webhook")
async def receive_webhook(request: Request):
    global latest_webhook_response
    payload = await request.json()
    if payload:
        latest_webhook_response = payload
        return JSONResponse(content={"status": "success"})
    else:
        raise HTTPException(status_code=400, detail="Invalid webhook payload")

@app.get("/latest-webhook")
async def get_latest_webhook_response(execution_id: str):
    if latest_webhook_response and latest_webhook_response.get('execution_id') == execution_id:
        return latest_webhook_response
    raise HTTPException(status_code=404, detail="No data found for this execution ID")

class ChatGPTRequest(BaseModel):
    prompt: str

@app.post("/api/chatgpt")
async def chatgpt_route(request: ChatGPTRequest):
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="API key is missing")

    requestBody = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": request.prompt}],
        "temperature": 0.7,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                json=requestBody,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "No content available")
            return JSONResponse(content={"content": content})
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail=f"API request failed: {e.response.text}")
    except httpx.RequestError as e:
        logger.error(f"Request error: {e}")
        raise HTTPException(status_code=500, detail="Request to OpenAI API failed")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from generator import main
import os

# Create an application using FastAPI named 'IFC Bridge Generator API'
app = FastAPI(title="IFC Bridge Generator API")

# Define the input schema for bridge generation parameters
# Default values are provided so the API can generate a bridge with missing user input
class BridgeParams(BaseModel):
    bridge_name: str = "MyBridge"

    deck_length: float = 40
    deck_width: float = 6
    deck_thickness: float = 0.8
    deck_height_above_ground: float = 5

    pier_width: float = 2
    pier_depth: float = 2
    pier_count: int = 3
    pier_edge_clear: float = 5.0

    girder_width: float = 0.35
    girder_depth: float = 1.5
    girder_count: int = 5

    crossbeam_width: float = 0.25
    crossbeam_depth: float = 0.6
    crossbeam_count: int = 6

    barrier_height: float = 1.2
    barrier_thickness: float = 0.2
    barrier_offset: float = 0.1

# Root endpoint used to confirm that the API service is running
@app.get("/")
def root():
    return {"message": "IFC Bridge Generator API is running"}

# Endpoint for generating an IFC bridge model from the submitted parameters
@app.post("/generate-ifc")
def generate_ifc(params: BridgeParams):
    try:
        # Convert the validated request body into a dictionary
        # and pass it to the bridge generator script
        file_path = main(params.model_dump())

        # Check that the IFC file was successfully created
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=500, detail="IFC file was not created.")

        # Extract the generated IFC file name from the full path
        filename = os.path.basename(file_path)

        # Return the filename together with a download link
        return {
            "status": "success",
            "filename": filename,
            "download_url": f"https://bridge-model-ifc-generator.onrender.com/download/{filename}"
        }

    # Catch unexpected errors and return them as HTTP 500 responses
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Endpoint for downloading a previously generated IFC file
@app.get("/download/{filename}")
def download_ifc(filename: str):
    # Check that the requested file exists
    if not os.path.exists(filename):
        raise HTTPException(status_code=404, detail="File not found.")

    # Return the IFC file as a downloadable response
    return FileResponse(
        path=filename,
        filename=filename,
        media_type="application/octet-stream"
    )
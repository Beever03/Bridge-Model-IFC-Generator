from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from generator import main
import os

app = FastAPI(title="IFC Bridge Generator API")


class BridgeParams(BaseModel):
    bridge_name: str = "MyBridge"

    deck_length: float = 40
    deck_width: float = 6
    deck_thickness: float = 0.8
    deck_height_above_ground: float = 5

    pier_width: float = 2
    pier_depth: float = 2
    pier_spacing: float = 10.0
    pier_edge_clear: float = 5.0

    girder_width: float = 0.35
    girder_depth: float = 1.5
    girder_spacing: float = 1.0

    crossbeam_width: float = 0.25
    crossbeam_depth: float = 0.6
    crossbeam_spacing: float = 4.0


@app.get("/")
def root():
    return {"message": "IFC Bridge Generator API is running"}


@app.post("/generate-ifc")
def generate_ifc(params: BridgeParams):
    try:
        # Run the IFC generator
        file_path = main(params.model_dump())

        # Check that the file was actually created
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=500, detail="IFC file was not created.")

        # Extract just the filename
        filename = os.path.basename(file_path)

        # Return simple JSON with clickable download URL
        return {
            "status": "success",
            "filename": filename,
            "download_url": f"https://bridge-model-ifc-generator.onrender.com/download/{filename}"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/download/{filename}")
def download_ifc(filename: str):
    # Check that the file exists
    if not os.path.exists(filename):
        raise HTTPException(status_code=404, detail="File not found.")

    # Return the IFC file as a download
    return FileResponse(
        path=filename,
        filename=filename,
        media_type="application/octet-stream"
    )
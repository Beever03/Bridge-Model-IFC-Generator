from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from generator import main
import os
import uuid

app = FastAPI(title="IFC Bridge Generator API")

OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)


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
        # Generate unique filename
        uid = uuid.uuid4().hex[:8]
        filename = f"{params.bridge_name}_{uid}.ifc"
        output_path = os.path.join(OUTPUT_DIR, filename)

        # Call generator
        generated_path = main(params.model_dump(), output_path)

        if not generated_path or not os.path.exists(generated_path):
            raise HTTPException(status_code=500, detail="IFC generation failed")

        return {
            "status": "success",
            "filename": filename,
            "download_url": f"https://bridge-model-ifc-generator.onrender.com/download/{filename}"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/download/{filename}")
def download_ifc(filename: str):
    file_path = os.path.join(OUTPUT_DIR, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream"
    )
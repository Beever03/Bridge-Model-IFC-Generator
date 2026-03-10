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
    deck_z: float = 5

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
        file_path = main(params.model_dump())

        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=500, detail="IFC file was not created.")

        return FileResponse(
            path=file_path,
            filename=os.path.basename(file_path),
            media_type="application/octet-stream",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
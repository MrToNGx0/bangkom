from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os

from app.core import config
from app.api.routes import router as api_router
from app.api.admin_routes import router as admin_router
from app.core.database import engine, Base

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Bangkom Subtitle Tool", version="2.0.0")

# Mount API routes
app.include_router(api_router, prefix="/api")
app.include_router(admin_router, prefix="/api/admin")

# Mount Static Files (Web Interface)
app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")


@app.get("/")
def root():
    index_path = os.path.join(config.STATIC_DIR, "index.html")

    if not os.path.exists(index_path):
        raise HTTPException(status_code=500, detail=f"index.html not found at {index_path}")

    return FileResponse(index_path)


@app.get("/admin")
def admin_page():
    admin_path = os.path.join(config.STATIC_DIR, "admin.html")
    if not os.path.exists(admin_path):
        raise HTTPException(status_code=500, detail="admin.html not found")
    return FileResponse(admin_path)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

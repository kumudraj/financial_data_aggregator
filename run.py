import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=5001,
        reload=True,
        log_level="critical",  # Only log critical logs from uvicorn
        workers=2,
        access_log=False,      # Disable uvicorn access logs
    )
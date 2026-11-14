from fastapi import FastAPI

app = FastAPI(
    title="InsightFlow AI",
    description="An intelligent AI-powered data analysis platform.",
    version="0.1.0",
)


@app.get("/")
def root():
    return {
        "message": "Welcome to InsightFlow AI",
        "status": "running",
    }


@app.get("/api/v1/health")
def health_check():
    return {
        "status": "healthy",
        "application": "InsightFlow AI",
        "version": "0.1.0",
    }

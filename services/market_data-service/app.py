# market_data-service/app.py
from fastapi import FastAPI, BackgroundTasks
from pipe_and_filter_core import main as fetch_main

app = FastAPI(title="Market Data Fetcher Service")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/fetch")
def start_fetch(background_tasks: BackgroundTasks):
    """
    Start full fetch in background thread.
    """
    background_tasks.add_task(fetch_main)
    return {"status": "fetch started"}

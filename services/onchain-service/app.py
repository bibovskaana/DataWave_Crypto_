from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from onchain_core import get_onchain_metrics

app = FastAPI(title="Onchain Service")

# CORS за Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.get("/onchain/{coin_id}")
def onchain_api(coin_id: str):
    data = get_onchain_metrics(coin_id)
    if data is None:
        return {"error": "Unable to fetch data"}
    return data

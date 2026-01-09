FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- DOWNLOAD NLTK DATA AT BUILD TIME ----
RUN python -m nltk.downloader vader_lexicon

COPY . .

# Streamlit користи 8501 порт
EXPOSE 8501

# CMD линијата мора да го стартува Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]

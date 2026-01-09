# lstm-service/lstm_core.py
import numpy as np
import torch
import torch.nn as nn
import pandas as pd

# ------------------------------------------------------------
# SIMPLE MIN-MAX SCALER
# ------------------------------------------------------------
class SimpleMinMaxScaler:
    def fit(self, data):
        self.min = data.min(axis=0)
        self.max = data.max(axis=0)
        return self

    def transform(self, data):
        return (data - self.min) / (self.max - self.min + 1e-8)

    def fit_transform(self, data):
        self.fit(data)
        return self.transform(data)

    def inverse_transform(self, data):
        return data * (self.max - self.min + 1e-8) + self.min


# ------------------------------------------------------------
# METRICS
# ------------------------------------------------------------
def mean_squared_error(y_true, y_pred):
    return np.mean((y_true - y_pred) ** 2)


def mean_absolute_percentage_error(y_true, y_pred):
    return np.mean(np.abs((y_true - y_pred) / y_true))


def r2_score(y_true, y_pred):
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    return 1 - ss_res / ss_tot


# ------------------------------------------------------------
# LSTM MODEL
# ------------------------------------------------------------
class LSTMModel(nn.Module):
    def __init__(self, input_size=5, hidden_size=32):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, batch_first=True)
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x):
        out, _ = self.lstm(x)
        out = out[:, -1, :]
        return self.fc(out)


def prepare_sequences(data, lookback=30):
    X, y = [], []
    for i in range(len(data) - lookback):
        X.append(data[i:i + lookback])
        y.append(data[i + lookback, 3])  # close price
    return np.array(X), np.array(y)


def train_lstm_model(data_list, lookback=30, epochs=30, lr=0.001):
    """
    data_list: list of dicts [{open, high, low, close, volume}, ...]
    """
    df = pd.DataFrame(data_list)[["open", "high", "low", "close", "volume"]].dropna()
    scaler = SimpleMinMaxScaler()
    scaled = scaler.fit_transform(df.values)

    X, y = prepare_sequences(scaled, lookback)
    split = int(len(X) * 0.7)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    X_train = torch.tensor(X_train, dtype=torch.float32)
    X_test = torch.tensor(X_test, dtype=torch.float32)
    y_train = torch.tensor(y_train, dtype=torch.float32).view(-1, 1)
    y_test = torch.tensor(y_test, dtype=torch.float32).view(-1, 1)

    model = LSTMModel()
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    for epoch in range(epochs):
        optimizer.zero_grad()
        loss = criterion(model(X_train), y_train)
        loss.backward()
        optimizer.step()

    # Prediction
    model.eval()
    pred_scaled = model(X_test).detach().numpy()

    dummy = np.zeros((len(pred_scaled), 5))
    dummy[:, 3] = pred_scaled[:, 0]
    pred = scaler.inverse_transform(dummy)[:, 3]

    dummy = np.zeros((len(y_test), 5))
    dummy[:, 3] = y_test.numpy().flatten()
    real = scaler.inverse_transform(dummy)[:, 3]

    rmse = np.sqrt(mean_squared_error(real, pred))
    mape = mean_absolute_percentage_error(real, pred)
    r2 = r2_score(real, pred)

    # Next-day prediction
    last_seq = torch.tensor(scaled[-lookback:].reshape(1, lookback, 5), dtype=torch.float32)
    next_scaled = model(last_seq).item()
    dummy = np.zeros((1, 5))
    dummy[:, 3] = next_scaled
    next_price = scaler.inverse_transform(dummy)[0][3]

    return model, pred, real, rmse, mape, r2, next_price

def calculate_signal(onchain: dict, sentiment_score: float):
    score = 0

    if onchain.get("NVT") is not None and onchain["NVT"] < 20:
        score += 1
    if onchain.get("MVRV") is not None and onchain["MVRV"] < 1:
        score += 1
    if onchain.get("whale_movements") is not None and onchain["whale_movements"] > 3:
        score += 1
    if onchain.get("TVL") is not None and onchain["TVL"] > 0:
        score += 1

    if sentiment_score > 0.2:
        score += 2
    elif sentiment_score < -0.2:
        score -= 2

    if score >= 4:
        return score, "BUY"
    elif score <= 1:
        return score, "SELL"
    else:
        return score, "HOLD"

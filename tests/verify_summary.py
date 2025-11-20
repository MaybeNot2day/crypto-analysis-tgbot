
import sys
import os
sys.path.append(os.getcwd())

import pandas as pd
from src.notifications.summary import MarketSummaryGenerator

def verify_summary():
    print("Verifying summary generation...")
    
    # Create dummy scores with new metrics
    scores = []
    for i in range(10):
        scores.append({
            "symbol": f"COIN{i}",
            "composite_score": 0.1 * i,
            "momentum_24h": 2.0 * i,
            "volatility_atr_pct": 1.5,
            "macd_signal": 1 if i > 5 else -1,
            "bb_position": 0.9 if i > 8 else -0.9 if i < 2 else 0,
            "rsi": 80 if i > 8 else 20 if i < 2 else 50,
            "outlier_type": "top" if i > 8 else "bottom" if i < 2 else None
        })
        
    df = pd.DataFrame(scores)
    outliers = df[df["outlier_type"].notna()]
    
    generator = MarketSummaryGenerator()
    summary = generator.generate_summary(outliers, df)
    
    print("\n" + "="*40)
    print(summary)
    print("="*40 + "\n")
    
    if "MACD" in summary and "RSI" in summary:
        print("✅ Summary contains new indicators")
    else:
        print("❌ Summary missing new indicators")

if __name__ == "__main__":
    verify_summary()

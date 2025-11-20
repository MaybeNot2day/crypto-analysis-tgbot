import sys
import os
sys.path.append(os.getcwd())

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.factors.calculator import FactorCalculator
from src.config import Config

def verify_analysis():
    print("Verifying analysis improvements...")
    
    # 1. Create dummy data
    print("Generating dummy data...")
    dates = pd.date_range(end=datetime.now(), periods=100, freq="1h")
    
    # Generate a random walk for prices
    np.random.seed(42)
    returns = np.random.normal(0, 0.01, 100)
    price = 100 * np.exp(np.cumsum(returns))
    
    # Generate volume
    volume = np.random.lognormal(10, 1, 100)
    
    df = pd.DataFrame({
        "timestamp": dates,
        "open": price,
        "high": price * 1.01,
        "low": price * 0.99,
        "close": price,
        "volume": volume
    })
    
    # 2. Initialize Calculator
    config = Config()
    calculator = FactorCalculator(config)
    
    # 3. Test Momentum (MACD)
    print("\nTesting Momentum (MACD)...")
    momentum = calculator.calculate_momentum(df)
    print(f"MACD Signal: {momentum.get('macd_signal')}")
    print(f"Trend Strength: {momentum.get('trend_strength')}")
    
    if momentum.get('macd_signal') is not None:
        print("✅ MACD calculation successful")
    else:
        print("❌ MACD calculation failed")

    # 4. Test Mean Reversion (BB, RSI)
    print("\nTesting Mean Reversion (Bollinger Bands, RSI)...")
    mr = calculator.calculate_mean_reversion(df)
    print(f"RSI: {mr.get('rsi')}")
    print(f"BB Position: {mr.get('bb_position')}")
    
    if mr.get('bb_position') is not None:
        print("✅ Bollinger Bands calculation successful")
    else:
        print("❌ Bollinger Bands calculation failed")

    # 5. Test Volatility (ATR)
    print("\nTesting Volatility (ATR)...")
    vol = calculator.calculate_volatility(df)
    print(f"ATR %: {vol.get('volatility_atr_pct')}")
    
    if vol.get('volatility_atr_pct') is not None:
        print("✅ ATR calculation successful")
    else:
        print("❌ ATR calculation failed")
        
    # 6. Test Composite Score
    print("\nTesting Composite Score...")
    composite = calculator.calculate_composite_score(
        momentum=momentum,
        mean_reversion=mr,
        carry={"carry_funding_annualized": 0.1, "carry_basis": 0.05},
        volume=calculator.calculate_volume_factors(df),
        volatility=vol
    )
    print(f"Composite Score: {composite}")
    
    if composite is not None:
        print("✅ Composite score calculation successful")
    else:
        print("❌ Composite score calculation failed")

    # 7. Test Outlier Detection (IQR)
    print("\nTesting Outlier Detection (IQR)...")
    # Create a list of dummy scores
    scores = []
    for i in range(20):
        scores.append({
            "symbol": f"COIN{i}",
            "composite_score": np.random.normal(0, 1)
        })
    # Add an outlier
    scores.append({"symbol": "OUTLIER_TOP", "composite_score": 5.0})
    scores.append({"symbol": "OUTLIER_BOTTOM", "composite_score": -5.0})
    
    results = calculator.identify_outliers(scores, use_iqr=True)
    
    outliers = [r for r in results if r["is_outlier"]]
    print(f"Found {len(outliers)} outliers out of {len(scores)} items")
    for o in outliers:
        print(f"  - {o['symbol']}: {o['composite_score']:.2f} ({o['outlier_type']})")
        
    if len(outliers) >= 2:
        print("✅ Outlier detection successful")
    else:
        print("❌ Outlier detection might be too strict or failed")

if __name__ == "__main__":
    verify_analysis()

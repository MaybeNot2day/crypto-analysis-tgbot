# Metrics Explained

This document explains all the metrics used in the Crypto Outlier Detection Dashboard in simple, easy-to-understand terms.

## 📈 Momentum Metrics

### Momentum (1h, 4h, 24h)
**What it measures:** How much the price has changed over a specific time period.

**Simple explanation:** 
- **Momentum 1h**: The percentage change in price over the last hour
- **Momentum 4h**: The percentage change in price over the last 4 hours
- **Momentum 24h**: The percentage change in price over the last 24 hours

**Example:** If Momentum 24h = +15%, the asset's price increased by 15% in the last 24 hours.

**What to look for:** 
- Positive values = price going up 📈
- Negative values = price going down 📉
- Large positive values = strong upward momentum (potential buying opportunity)
- Large negative values = strong downward momentum (potential selling signa
### Momentum Percentile
**What it measures:** Where the current momentum ranks compared to recent history.

**Simple explanation:** If Momentum Percentile = 75%, it means the current momentum is higher than 75% of recent momentum values for this asset.

**What to look for:**
- High percentile (>80%) = unusually strong momentum compared to recent history
- Low percentile (<20%) = unusually weak momentum compared to recent history

---

## 🔄 Mean Reversion Metrics

### Mean Reversion Z-Score
**What it measures:** How far the current price is from its recent average price.

**Simple explanation:** 
- Z-Score = 0: Price is exactly at the average
- Z-Score = +2: Price is 2 standard deviations above average (very high)
- Z-Score = -2: Price is 2 standard deviations below average (very low)

**What to look for:**
- High positive values (+2 or more) = price is unusually high, might drop soon (sell signal)
- High negative values (-2 or less) = price is unusually low, might bounce back (buy signal)
- Values near 0 = price is near average, no strong signal

**Trading idea:** Buy when price is very low (negative z-score), sell when price is very high (positive z-score).

### RSI (Relative Strength Index)
**What it measures:** Whether an asset is overbought (too many buyers) or oversold (too many sellers).

**Simple explanation:** RSI ranges from 0 to 100.
- **RSI > 70**: Asset is "overbought" - price might drop soon
- **RSI < 30**: Asset is "oversold" - price might rise soon
- **RSI 30-70**: Normal range, no strong signal

**What to look for:**
- RSI above 70 = potentially overvalued, consider selling
- RSI below 30 = potentially undervalued, consider buying

---

## 💰 Carry Metrics

### Carry Funding Annualized
**What it measures:** How much you'd earn (or pay) per year by holding a futures contract instead of the spot asset.

**Simple explanation:** 
- Positive values = You earn money by holding futures (market expects price to go up)
- Negative values = You pay money to hold futures (market expects price to go down)

**Example:** If Carry Funding Annualized = -20%, you'd pay 20% per year to hold a futures position. This suggests the market expects the price to drop.

**What to look for:**
- High negative values = Market expects price to fall (bearish signal)
- High positive values = Market expects price to rise (bullish signal)

### Carry Basis
**What it measures:** The difference between the futures price and the spot price, as a percentage.

**Simple explanation:**
- **Basis > 0**: Futures price is higher than spot price (premium)
- **Basis < 0**: Futures price is lower than spot price (discount)

**What to look for:**
- Large positive basis = Market is bullish (futures trading above spot)
- Large negative basis = Market is bearish (futures trading below spot)

---

## 📊 Volume Metrics

### Volume Momentum (1h, 4h, 24h)
**What it measures:** How much trading volume has changed compared to earlier periods.

**Simple explanation:**
- **Volume Momentum 1h**: Percentage change in trading volume compared to 1 hour ago
- **Volume Momentum 4h**: Percentage change in trading volume compared to 4 hours ago
- **Volume Momentum 24h**: Percentage change in trading volume compared to 24 hours ago

**Example:** If Volume Momentum 24h = +50%, trading volume increased by 50% compared to yesterday.

**What to look for:**
- Large positive values = Much more trading activity (could indicate strong interest or news)
- Large negative values = Much less trading activity (could indicate loss of interest)
- High volume momentum often accompanies significant price moves

### Volume Anomaly Z-Score
**What it measures:** Whether current trading volume is unusually high or low compared to recent history.

**Simple explanation:** Similar to price z-score, but for volume.
- Z-Score = 0: Volume is normal
- Z-Score = +2: Volume is 2x higher than normal (unusually high)
- Z-Score = -2: Volume is 2x lower than normal (unusually low)

**What to look for:**
- High positive values (+2 or more) = Unusually high trading volume (could indicate news, manipulation, or major interest)
- High negative values (-2 or less) = Unusually low trading volume (could indicate lack of interest)
- Volume spikes often precede or accompany significant price movements

### Volume Percentile
**What it measures:** Where current volume ranks compared to recent volume history.

**Simple explanation:** If Volume Percentile = 90%, current volume is higher than 90% of recent volume measurements.

**What to look for:**
- High percentile (>80%) = Volume is unusually high (watch for price movement)
- Low percentile (<20%) = Volume is unusually low (market might be quiet)

### Volume-Price Divergence
**What it measures:** Whether volume changes and price changes are moving in the same direction or opposite directions.

**Simple explanation:**
- **Positive divergence**: When volume increases but price decreases (or vice versa) - signals potential reversal
- **Negative divergence**: When volume and price move together - confirms the trend
- **Zero divergence**: Volume and price changes are uncorrelated

**What to look for:**
- High positive divergence = Volume and price moving in opposite directions (potential reversal signal)
- High negative divergence = Volume and price moving together (trend confirmation)
- Can indicate if a price move is supported by volume or not

---

## 🎯 Composite Score

**What it measures:** A single number that combines all factors (momentum, mean reversion, carry, and volume) into one overall score.

**Simple explanation:** 
- Scores range from -1 to +1
- **Positive scores** = Generally bullish signals (multiple factors suggest upward movement)
- **Negative scores** = Generally bearish signals (multiple factors suggest downward movement)
- **Near zero** = Mixed or neutral signals

**How it's calculated:** Each factor (momentum, mean reversion, carry, volume) is normalized and weighted:
- Momentum: 25% weight
- Mean Reversion: 25% weight
- Carry: 30% weight
- Volume: 20% weight

**What to look for:**
- **High positive scores (>0.5)**: Strong bullish signal across multiple factors
- **High negative scores (<-0.5)**: Strong bearish signal across multiple factors
- **Extreme scores** (close to +1 or -1) = Multiple factors aligning, potential outlier

---

## 🚨 Outlier Detection

### Is Outlier
**What it measures:** Whether an asset is flagged as an outlier based on its composite score.

**Simple explanation:** 
- **True** = This asset is behaving unusually compared to other assets
- **False** = This asset is behaving normally

**How outliers are detected:**
1. **Z-Score method**: Assets with composite scores more than 2 standard deviations from the mean
2. **Top/Bottom N**: The top 10 and bottom 10 assets by composite score

### Outlier Type
**What it measures:** What kind of outlier the asset is.

**Simple explanation:**
- **"top"** = Outlier with high composite score (bullish outlier, potential buying opportunity)
- **"bottom"** = Outlier with low composite score (bearish outlier, potential selling signal)
- **None** = Not flagged as an outlier

**What to look for:**
- **Top outliers**: Multiple bullish factors aligning - could be a strong buy signal
- **Bottom outliers**: Multiple bearish factors aligning - could be a strong sell signal
- Outliers often represent opportunities but can also indicate overvaluation/undervaluation

---

## 💡 How to Use These Metrics

### For Trading Decisions:
1. **Start with Composite Score**: Get a quick overview of the asset's overall signal
2. **Check Outlier Status**: Outliers often represent the best opportunities
3. **Dive into Individual Factors**: Understand why an asset is flagged as an outlier
4. **Look for Confirmation**: Multiple factors pointing in the same direction = stronger signal

### Red Flags to Watch:
- **High momentum + High RSI**: Price might be overextended (overbought)
- **Low momentum + Low RSI**: Price might be oversold (potential bounce)
- **High volume anomaly + Price divergence**: Could indicate manipulation or major news
- **Negative carry + High basis**: Market expectations might be shifting

### Green Flags:
- **Multiple factors aligning**: Momentum, volume, and carry all pointing in same direction
- **Volume supporting price moves**: High volume momentum with matching price momentum
- **Mean reversion opportunities**: High z-score (overvalued) or low z-score (undervalued) with RSI confirmation

---

## 📝 Notes

- **All metrics are calculated relative to BTC** (price_btc shows the normalized price)
- **Metrics are updated hourly** - values reflect the most recent data snapshot
- **Percentile metrics** compare current values to the asset's own historical data
- **Z-scores** compare current values to recent averages (last 24 hours of data)
- **Missing data** (null/NaN values) indicate insufficient historical data for calculation

---

*Last updated: November 2025*

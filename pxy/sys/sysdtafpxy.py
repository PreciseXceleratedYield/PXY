//@version=5
indicator("75% Full Range Flip Candles", overlay=true)

// Calculate standard candle properties
isRawGreen = close >= open

// 1. Calculate Average Candle Height using ATR 14
atrValue = ta.atr(14)

// 2. Set threshold to 75% of the ATR 14 average full candle height
threshold = atrValue * 0.75

// 3. Use persistent variables to track custom candle state
var bool isCustomGreen = true

// 4. Check for flip condition using the full candle height (High to Low)
if isCustomGreen and not isRawGreen and (high - low) >= threshold
    isCustomGreen := false // Flip to Red
else if not isCustomGreen and isRawGreen and (high - low) >= threshold
    isCustomGreen := true  // Flip to Green

// 5. Color Assignment
candleColor = isCustomGreen ? color.green : color.red

// 6. Plotting
plotcandle(open, high, low, close, title="75% Full Range Candles", 
          color=candleColor, wickcolor=candleColor, bordercolor=candleColor)




# sysdeptpxy.py 🟩 🟥
# sysdeptpxy.py 

from sysdthapxy import get_ha_data

def get_candle_visual(df=None, last_n=21):
    ha_close, ha_open, ha_color, df = get_ha_data(df=df)

    if ha_color is None:
        return ""

    visual = "".join(["🟩" if c=="green" else "🟥" for c in ha_color.iloc[-last_n:]])
    return visual


# -------- Self-test --------
if __name__ == "__main__":
    visual = get_candle_visual()
    print(visual)

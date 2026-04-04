# syshkinpxy.py
from sysdthapxy import get_ha_data
from colorama import Fore, Style, init

# Initialize Colorama
init(autoreset=True)

# -------------------- HA Flip Detection --------------------
def detect_ha_flip_signal(df=None):
    ha_close, ha_open, ha_color, df = get_ha_data(df=df)
    if ha_color is None or len(ha_color) < 2:
        return "NONE", 0, 1, 1

    last_closed = ha_color.iloc[-2]
    current_candle = ha_color.iloc[-1]

    # ---------------- Detect flips ----------------
    if last_closed == 'red' and current_candle == 'green':
        signal = "BUY"
    elif last_closed == 'green' and current_candle == 'red':
        signal = "SELL"
    else:
        if len(ha_color) >= 3:
            last_two = ha_color.iloc[-3:-1].tolist()
            if last_two == ['green', 'green']:
                signal = "BULL"
            elif last_two == ['red', 'red']:
                signal = "BEAR"
            else:
                signal = "NONE"
        else:
            signal = "NONE"

    # ---------------- Past depth (previous color streak) ----------------
    past_depth = 1
    for color in reversed(ha_color.iloc[:-1]):
        if color == last_closed:
            past_depth += 1
        else:
            break

    # ---------------- Current CE/PE depth (active streak) ----------------
    ce_depth = pe_depth = 1
    current_depth = 1
    for color in reversed(ha_color):
        if color == current_candle:
            current_depth += 1
        else:
            break

    if current_candle == 'green':
        ce_depth = current_depth
    else:
        pe_depth = current_depth

    return signal, past_depth, ce_depth, pe_depth


# -------------------- Self-runnable test --------------------
if __name__ == "__main__":
    signal, past_depth, ce_depth, pe_depth = detect_ha_flip_signal()

    # Color coding
    if signal in ["BUY", "BULL"]:
        color = Fore.GREEN
    elif signal in ["SELL", "BEAR"]:
        color = Fore.RED
    else:
        color = Fore.YELLOW

    # Labels + values
    left_text = f"{color}Hkin:{signal}{Style.RESET_ALL}"
    middle_text = f"{color}Past:{past_depth}{Style.RESET_ALL}"
    right_text = f"{color}CE:{ce_depth} PE:{pe_depth}{Style.RESET_ALL}"

    # Compute spacing for total width = 42
    total_width = 42
    plain_left = f"Hkin:{signal}"  # length without color codes
    plain_middle = f"Past:{past_depth}"
    plain_right = f"CE:{ce_depth} PE:{pe_depth}"
    space_width = total_width - len(plain_left) - len(plain_middle) - len(plain_right)
    if space_width < 0:
        space_width = 1
    spacing = " " * space_width

    # Print single line
    print(left_text + middle_text + spacing + right_text)

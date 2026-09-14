from rich import print
from rich.table import Table
import rich.box as box
from syscolrpxy import SILVER, UNDERLINE, RED, GREEN, YELLOW, RESET, BRIGHT_YELLOW, BRIGHT_RED, BRIGHT_GREEN, BOLD, GREY

# Large legal text block maintained
copyright_notice = (
    "The PXY® trading tool, including its source code, algorithmic logic, user interfaces, documentation, "
    "and design elements, is protected by international copyright laws, proprietary intellectual property treaties, "
    "and domestic regulations. All rights are reserved globally by PXY® and PreciseXceleratedYield Pvt Ltd™. "
    "Any unauthorized reproduction, modification, distribution, decompilation, reverse engineering, or public display "
    "of this software, in whole or in part, is strictly prohibited without explicit written consent. "
    "Violations constitute severe infringement and will trigger immediate legal action, including injunctive relief, "
    "substantial statutory financial penalties, and criminal prosecution where applicable. PXY® actively monitors "
    "and enforces its intellectual property rights to the fullest extent of law."
)

# Maintain exact same box width
width = 38

# Split text into original individual words to process sequentially
words = copyright_notice.split()
perfect_lines = []
current_line_words = []
current_len = 0

for word in words:
    # Check length if we were to add this word normally with a space
    added_len = len(word) + (1 if current_line_words else 0)
    
    if current_len + added_len <= width:
        current_line_words.append(word)
        current_len += added_len
    else:
        # Word doesn't fit normally. Determine how much room is left on this line
        space_available = width - current_len - (1 if current_line_words else 0)
        
        # If there's enough room for a decent fragment and a hyphen (at least 2 chars of the word + '-')
        if space_available >= 3:
            if current_line_words:
                # Add space before the fragment if it's not the start of the line
                fragment_size = space_available - 1
                word_fragment = word[:fragment_size]
                remaining_word = word[fragment_size:]
                current_line_words.append(word_fragment + "-")
            else:
                fragment_size = space_available
                word_fragment = word[:fragment_size]
                remaining_word = word[fragment_size:]
                current_line_words.append(word_fragment + "-")
                
            perfect_lines.append(" ".join(current_line_words))
            current_line_words = [remaining_word]
            current_len = len(remaining_word)
        else:
            # Not enough space for a hyphenated break; push the entire word to the next line
            # Justify the current finished line before storing it
            if current_line_words:
                line_str = " ".join(current_line_words)
                total_chars = sum(len(w) for w in current_line_words)
                total_spaces_needed = width - total_chars
                
                if len(current_line_words) > 1:
                    spaces_between = total_spaces_needed // (len(current_line_words) - 1)
                    extra_spaces = total_spaces_needed % (len(current_line_words) - 1)
                    justified_line = ""
                    for i, w in enumerate(current_line_words[:-1]):
                        pad = spaces_between + (1 if i < extra_spaces else 0)
                        justified_line += w + (" " * pad)
                    justified_line += current_line_words[-1]
                    perfect_lines.append(justified_line)
                else:
                    perfect_lines.append(line_str.ljust(width))
            
            current_line_words = [word]
            current_len = len(word)

# Handle the absolute last line remaining in the buffer
if current_line_words:
    last_line = " ".join(current_line_words)
    perfect_lines.append(last_line.ljust(width))

# Recombine into a single string for the table layout
final_justified_notice = "\n".join(perfect_lines)

# Create a table with dim border configuration using a valid rich box style
table = Table(border_style="dim", box=box.SQUARE)

# Add the column header centered exactly
table.add_column("PXY® PreciseXceleratedYield Pvt Ltd™", style="dim", justify="center")

# Add the row with the perfect-width text string
table.add_row(final_justified_notice, style="dim")

# Display the table layout
print(table)


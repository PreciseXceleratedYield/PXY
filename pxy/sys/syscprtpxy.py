from rich import print
from rich.table import Table
import rich.box as box
import textwrap
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
    "and ruthlessly enforces its intellectual property rights to the fullest extent of law."
)

# Maintain exact same box width
width = 38

# Break the long text into 38-character wrapped lines
raw_lines = textwrap.wrap(copyright_notice, width=width, break_long_words=False)
perfect_lines = []

for idx, line in enumerate(raw_lines):
    words = line.split()
    
    # Don't stretch the absolute last line of a paragraph or lines with single words
    if idx == len(raw_lines) - 1 or len(words) <= 1:
        perfect_lines.append(line.ljust(width))
        continue
    
    # Calculate exact space allocation needed to hit exactly 38 characters
    total_chars = sum(len(w) for w in words)
    total_spaces_needed = width - total_chars
    
    # Dynamically spread the whitespaces evenly across all word gaps
    spaces_between_words = total_spaces_needed // (len(words) - 1)
    extra_spaces = total_spaces_needed % (len(words) - 1)
    
    justified_line = ""
    for i, word in enumerate(words[:-1]):
        # Inject primary calculated space padding along with fractional remaining spaces
        space_padding = spaces_between_words + (1 if i < extra_spaces else 0)
        justified_line += word + (" " * space_padding)
    justified_line += words[-1]
    
    perfect_lines.append(justified_line)

# Recombine into a single string for the table layout
final_justified_notice = "\n".join(perfect_lines)

# Create a table with dim border configuration using a valid rich box style
table = Table(border_style="dim", box=box.SQUARE)

# Add the column header centered exactly (this manages the layout alignment rules)
table.add_column("PXY® PreciseXceleratedYield Pvt Ltd™", style="dim", justify="center")

# Add the justified content block (Removed the invalid justify argument)
table.add_row(final_justified_notice, style="dim")

# Display the table layout
print(table)



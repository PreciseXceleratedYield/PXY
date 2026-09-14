from rich import print
from rich.table import Table
import textwrap
from syscolrpxy import SILVER, UNDERLINE, RED, GREEN, YELLOW, RESET, BRIGHT_YELLOW, BRIGHT_RED, BRIGHT_GREEN, BOLD, GREY

# Expanded Copyright Notice
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

# Set the desired width to match the header length
width = 38

# Use textwrap to format the text with a fixed width
wrapped_notice = textwrap.fill(copyright_notice, width, break_long_words=False)

# Create a table with dim border
table = Table(border_style="dim")

# Add the column header centered
table.add_column("PXY® PreciseXceleratedYield Pvt Ltd™", style="dim", justify="center")

# Add the row with full text justification for clean margins
table.add_row(wrapped_notice, style="dim", justify="full")

# Display the table without extra space
print(table)

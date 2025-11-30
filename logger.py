# logger.py
import re
from datetime import datetime
from rich.console import Console
from rich.markup import escape
from field_meta import FIELD_META

# Shared Console Instance
console = Console()

def _timestamp():
    """Returns the current time formatted for the log."""
    return f"[dim]{datetime.now().strftime('%H:%M:%S')}[/dim]"

def info(source, message, style="cyan"):
    """
    Standard System Event Log.
    Automatically escapes brackets so errors like '[Errno 98]' don't break Rich.
    """
    safe_message = escape(str(message)) # <--- Escape brackets
    tag_color = f"bold {style}"
    console.print(f"{_timestamp()} [{tag_color}]{source:<10}[/{tag_color}] {safe_message}")

def warn(source, message):
    """Warning Log."""
    safe_message = escape(str(message))
    console.print(f"{_timestamp()} [bold yellow]{source:<10}[/bold yellow] {safe_message}")

def error(source, message):
    """Error Log."""
    safe_message = escape(str(message))
    console.print(f"{_timestamp()} [bold red]{source:<10}[/bold red] {safe_message}")

def telemetry(device_name, field, value, is_rtl=True):
    """
    Formatted Sensor Data Log.
    """
    meta = FIELD_META.get(field, ("", "none", "", ""))
    unit = meta[0]
    
    display_val = f"{value}"
    if unit:
        display_val += f" {unit}"

    if is_rtl:
        icon = "📡"
        color_dev = "bold deep_sky_blue1"
        color_val = "bold white"
    else:
        icon = "🖥️ "
        color_dev = "dim blue"
        color_val = "dim white"

    # We escape the device name just in case it has weird characters
    safe_dev = escape(str(device_name))

    console.print(
        f"{_timestamp()} {icon} [{color_dev}]{safe_dev:<25}[/{color_dev}] "
        f"| [bold white]{field:<18}[/bold white] : [{color_val}]{display_val}[/{color_val}]"
    )

def raw_json(source, raw_str):
    """
    'Tron' style raw JSON formatter. 
    Manual parsing is used here so we don't escape the whole thing.
    """
    s = raw_str
    # 1. Hide structure
    s = s.replace('{', '§OB§').replace('}', '§CB§')
    s = s.replace('[', '§LB§').replace(']', '§RB§')
    s = s.replace(',', '§CM§')

    # 2. Format Keys (White)
    s = re.sub(r'"([^"]+)"\s*:', r'[dim]"[/dim][bold white]\1[/bold white][dim]":[/dim]', s)
    
    # 3. Format Values (Cyan)
    s = re.sub(r'(\[dim\]":\[/dim\]\s*)"([^"]+)"', r'\1[dim]"[/dim][bold cyan]\2[/bold cyan][dim]"[/dim]', s)
    s = re.sub(r'(\[dim\]":\[/dim\]\s*)([0-9.-]+|true|false|null)', r'\1[bold cyan]\2[/bold cyan]', s)

    # 4. Restore structure
    s = s.replace('§OB§', '[dim]{[/dim]').replace('§CB§', '[dim]}[/dim]')
    s = s.replace('§LB§', '[dim][[/dim]').replace('§RB§', '[dim]][/dim]')
    s = s.replace('§CM§', '[dim],[/dim]')

    console.print(
        f"{_timestamp()} 🐞 [bold deep_sky_blue1]{source:<25}[/bold deep_sky_blue1] "
        f"| [bold cyan]RAW[/bold cyan]                : {s}"
    )
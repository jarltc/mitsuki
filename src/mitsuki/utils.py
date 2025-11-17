from datetime import datetime as dt
from pathlib import Path
import yaml

mitsuki_dir = Path.home()/".mitsuki"

def load_config() -> dict:
    yml_dir = Path.home()/".mitsuki"/"config.yml"
    if not yml_dir.exists():
        raise ValueError("Config file in ~/.mitsuki not found!")
    with open(yml_dir, 'r') as file:
        config = yaml.safe_load(file)
    return config

def write_skipped(raw:list, jpg:list):
    fname = dt.now().strftime("%y%m%d-%H%M")
    logfile = mitsuki_dir/"logs"/f"{fname}.txt"
    logfile.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "##### Skipped transfers #####",
        "RAW:",
        *raw,
        "",
        "JPG:",
        *jpg,
        "######### EOF #########",
    ]
    logfile.write_text("\n".join(map(str, lines)) + "\n")
    
    return logfile
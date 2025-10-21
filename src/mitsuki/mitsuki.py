#!/Users/jarl/miniconda3/bin/python
import sys
from datetime import datetime as dt
from datetime import timezone
from pathlib import Path
from shutil import copy2 as copy
from time import sleep

from rich.console import Console
from rich.progress import track

from .utils import load_config, write_skipped

root = Path(__file__).parent.resolve()  # directory where script is stored

config = load_config()

DRY_RUN = config["DRY_RUN"]
DATE_FORMAT = config["DATE_FORMAT"]
BACKUP_DIR = config["DST"]
SDCARD = config["SRC"]
RAW_EXT = config["RAW_EXT"]
JPG_EXT = config["JPG_EXT"]

# create directory
class ImageFolder:
    def __init__(self, date:dt) -> None:
        self.date = date
        self.folder_name = dt.strftime(self.date, DATE_FORMAT)
        self.year = self.date.strftime("%Y")
        self.month = self.date.strftime("%B")
        self.day = self.date.strftime("%d")

        self.basedir = BACKUP_DIR
        self.folder = Path(BACKUP_DIR, self.year, self.folder_name)  # backup_dir/2025/250630/...
        self.jpg = self.folder/"JPG"
        self.raw = self.folder/"RAW"
        
        self.jpg.mkdir(exist_ok=True, parents=True)
        self.raw.mkdir(exist_ok=True, parents=True)
            
def check_drive(path:Path, console:Console, kind:str):
    kind_full = {"src":"Source", "dst":"Destination"}
    
    if path.exists():
        console.print(f"{kind_full[kind]} {path} [bold green]OK")
        return True
    else:
        console.print(f"{kind_full[kind]} {path} [bold red]missing!")
        return False
    

def transfer(transfer_list:dict, skipped:list, ext:str, console:Console):
    """Transfer files from src to dst found in transfer_list.
    transfer_list is a dict of Paths to images in the source directory paired with their associated ImageFolders,
    i.e. Path(SDCard/DCIM/image): ImageFolder.jpg or ImageFolder.raw

    Args:
        transfer_list (dict): Dictionary of transfers to be made.
        skipped (list): List of skipped file if found to already exist on the drive.
        ext (str): File extension used for updating track().
    """

    # loop through dictionary of Path(SDCard/DCIM/image): ImageFolder.jpg/raw
    desc = f"Transferring {ext}..."
    for source_item, output_folder in track(transfer_list.items(), description=desc):
        if DRY_RUN:
            sleep(0.2)
        else:
            dst = output_folder/(source_item.name)  # .name includes the extension
            try:
                copy(source_item, dst)
            except Exception:
                console.print(f"[bold red]Problem encountered when transferring {source_item.name}")
                console.print_exception()
                
    
def cli():
    console = Console()
    sdcardOK = False
    backupOK = False

    sd_card = Path(SDCARD)
    sdcardOK = check_drive(sd_card, console, "src")
    
    backup_dir = Path(BACKUP_DIR)
    backupOK = check_drive(backup_dir, console, "dst")

    if not (sdcardOK and backupOK):
        console.print("[bold red]ERROR: One or both of the required drives is missing. Exiting program.")
        sys.exit()
    
    # record all generated ImageFolder instances and associate them with a datetime
    folder_dict = {}

    # record all the transfers to be made
    raw_transfers = {}
    jpg_transfers = {}
    skipped_raw = []
    skipped_jpg = []
    
    # locate all raw/jpg files on SDCARD
    raw_files = Path(SDCARD).rglob("*"+RAW_EXT, case_sensitive=False)
    jpg_files = Path(SDCARD).rglob("*"+JPG_EXT, case_sensitive=False)

    # create ImageFolder instances
    with console.status("[bold blue]Locating images...") as status:
        # I'm doing JPG first because it's more likely to have JPGs with no associated RAW files
        status.update("[bold green]Scanning JPG files...")
        for item in jpg_files:
            created = item.stat().st_mtime  # last modified time
            dt_created = dt.fromtimestamp(created, tz=timezone.utc)  # convert to utc datetime
            image_folder = ImageFolder(dt_created)
            if (image_folder.jpg/item.name).exists():
                skipped_jpg.append(item.stem)
            else: 
                folder_dict[dt_created.date()] = image_folder
                jpg_transfers[item] = image_folder.jpg
        
        jpg_counter = len(jpg_transfers)
        status.console.print(f"Found {jpg_counter} {JPG_EXT} files")
        
        status.update("[bold green]Scanning RAW files...")
        for item in raw_files:
            created = item.stat().st_mtime
            date_created = dt.fromtimestamp(created, tz=timezone.utc).date()
            image_folder = folder_dict[date_created]
            if (image_folder.raw/item.name).exists():
                skipped_jpg.append(item.stem)
            else: 
                folder_dict[dt_created.date()] = image_folder
                raw_transfers[item] = image_folder.raw
    
        raw_counter = len(raw_transfers)
        status.console.print(f"Found {raw_counter} {RAW_EXT} files")

    # actual transfer
    if jpg_counter > 0:
        transfer(jpg_transfers, skipped_jpg, ext=JPG_EXT, console=console)
    else:
        console.print(f"No {JPG_EXT} transfers")

    if raw_counter > 0:
        transfer(raw_transfers, skipped_raw, ext=RAW_EXT, console=console)
    else:
        console.print(f"No {RAW_EXT} transfers")

    console.print("[bold green]Transfers complete!")
    if (len(skipped_jpg) > 0) or (len(skipped_raw) > 0):
        logfile = write_skipped(skipped_raw, skipped_jpg)
        console.print(f"Skipped existing {len(skipped_raw)} ORF and {len(skipped_jpg)} JPG files, details in {logfile}")
    else:
        console.print("No transfers skipped")

if __name__ == "__main__":
    cli()

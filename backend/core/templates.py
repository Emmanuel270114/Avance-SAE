import os
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "frontend", "Templates"))
static = StaticFiles(directory=os.path.join(BASE_DIR, "frontend", "static"))

if __name__ == "__main__":
    print(BASE_DIR)
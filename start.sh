BASEDIR=$(dirname "$0")

if ! command -v ffmpeg &> /dev/null
then
    echo "ffmpeg could not be found"
    echo "Debian/Ubuntu: sudo apt install ffmpeg"
    echo "Arch: sudo pacman -S ffmpeg"
    echo "Fedora: sudo dnf install ffmpeg"
    exit
fi

if ! command -v python3.11 &> /dev/null
then
    echo "python3.11 could not be found"
    echo "Download it from https://www.python.org/downloads/"
    exit
fi

python3.11 -m pip install --upgrade pip
if [ ! -d "$BASEDIR/venv" ]; then
    python3.11 -m pip install --user virtualenv
    python3.11 -m virtualenv venv
fi
source venv/bin/activate

pip install -r requirements.txt
pip install git+https://github.com/shahriyardx/easy-pil@3.11
clear

python main.py
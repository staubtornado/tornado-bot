BASEDIR=$(dirname "$0")

if [ ! -d "$BASEDIR/venv" ]; then
    python3.11 -m pip install --user virtualenv
    python3.11 -m virtualenv venv
fi
source venv/bin/activate

pip install -r requirements.txt
pip install git+https://github.com/shahriyardx/easy-pil@3.11
clear

python main.py
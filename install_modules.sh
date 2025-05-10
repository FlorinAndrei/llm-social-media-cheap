if [ ! -d ".venv" ]; then
    python3.12 -m venv .venv || exit 1
fi

. .venv/bin/activate || exit 1

pip install --upgrade pip
pip install --upgrade wheel setuptools
pip install -r requirements.txt

screen -S reddit -dm bash -c "source .venv/bin/activate; python -u reddit_comment_exporter.py | tee -a app.log"

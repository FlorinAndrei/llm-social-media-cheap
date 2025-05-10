if [ $# -ne 1 ]; then
    echo "Usage: $0 <notebook_file>"
    exit 1
fi

nb_file=$1
log_file_base="log-$(basename $nb_file)-$(date +%Y-%m-%d-%H-%M-%S)"
stdout_log_file="${log_file_base}-stdout.log"
stderr_log_file="${log_file_base}-stderr.log"

screen -S unsloth -dm bash -c "source .venv/bin/activate; jupyter nbconvert --to script $nb_file --stdout | python -u > >(tee \"$stdout_log_file\") 2> >(tee \"$stderr_log_file\" >&2)"

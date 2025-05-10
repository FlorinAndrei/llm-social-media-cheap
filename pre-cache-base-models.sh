. .venv/bin/activate

for model in \
    unsloth/gemma-3-27b-it-bnb-4bit \
    unsloth/gemma-3-27b-it \
    unsloth/meta-llama-3.1-8b-instruct-bnb-4bit \
    ; do
    huggingface-cli download $model --max-workers 1
done

# llm-social-media-cheap
LLMs fine-tuned with social media comments on consumer hardware

There is a companion article for this repo on Medium, read it:

https://medium.com/data-science-collective/train-llms-to-talk-like-you-on-social-media-using-consumer-hardware-c88750a56e6d

The goal is to fine-tune LLMs with dozens of billions of weights on hardware you may already have, such as a good gaming PC. The only real constraint is the size of the GPU VRAM: the bigger, the better. I used an RTX 3090, which has 24 GB of VRAM.

# Installation

This is an emergent field, so all tools and libraries are in flux. The latest versions may not always work. I did my best to find a combination that works well now (April 2025). When you're reading this, perhaps the bugs have been fixed and the latest versions will work - but, if not, then follow these instructions.

I did all this work on a PC running Ubuntu 24.04, with Python 3.12.3. I could not use Python 3.13, Unsloth does not currently support it.

I had the NVIDIA drivers 550.144.03 installed at the OS level. You only need to install the drivers this way. You do not need to install any CUDA libraries at the OS level - they will get pulled in as Python modules.

Run `install_modules.sh` to create the Python venv and install all modules in it. The versions are set in `requirements.txt`.

Run `install_dependencies.sh` to install specific versions of `llama.cpp` and `unsloth_zoo` in this repo. The script will also patch `unsloth_zoo`. All this is needed to fix Unsloth bugs. It doesn't matter if you have a more recent version of `llama.cpp` installed at the OS level, you still need to run this script, unless Unsloth has fixed these issues meanwhile.

`unsloth_zoo` will also be installed as a module in the venv, but it has a bug; my script will install this module in the current folder, which has higher priority than the installed Python modules, and patch it to fix the bug. The notebooks will use the patched `unsloth_zoo` from the current folder.

# Dataset

I've downloaded all comments I ever posted on Reddit, the article explains the procedure. Using the `reddit_comment_exporter.py` script, I've downloaded all the parent entities to my comments. The parent entities are the prompts, my comments are the answers. This way, the models were trained in the typical prompt/answer fashion.

Use `run-reddit-script.sh` to invoke the Python exporter with the proper context.

But any dataset will work, as long as it's big enough, and you put it in a file called `conversations.csv` with a structure like this (I'm showing ASCII art, not the actual CSV contents):

```
+---------------+-------------------------+
| parent_text   | comment_body            |
+---------------+-------------------------+
| Is water wet? | Of course it is.        |
| How are you?  | I'm good, thanks!       |
| Name a color. | Blue. Or green. Or red. |
+---------------+-------------------------+
```

# Training

The `training-llama3.ipynb` and `training-gemma3.ipynb` notebooks do all the training. The Medium article explains the notebooks in detail. Use `run-training.sh` to invoke the training notebooks with the proper context, and also to run them detached, in a Screen session, which will allow you to invoke training remotely, over an ssh session - you do not need to be logged in and running Jupyter on the local desktop to do training.

The `visualize-training.ipynb` notebook will show a few model metrics. You can run it after training is done.

# Inference

Use the `inference-llama3.ipynb` and `inference-gemma3.ipynb` notebooks to run inference with your trained models.

`training-gemma3.ipynb` also describes a method to load your trained model in Ollama.

# install llama.cpp
wget https://github.com/ggml-org/llama.cpp/archive/refs/tags/b5137.zip
unzip b5137.zip
rm -rf llama.cpp b5137.zip
mv llama.cpp-b5137 llama.cpp
cd llama.cpp
# change this to ON if you have CUDA installed, but it's not mandatory just for fine-tuning
cmake -B build -DGGML_CUDA=OFF
cmake --build build --config Release
ln -s ./build/bin/llama-quantize llama-quantize
ln -s ./build/bin/llama-gguf-split llama-gguf-split
cd ..

# install unsloth_zoo
wget https://files.pythonhosted.org/packages/40/18/bee4d2e93a567fcbd30719a8b2a627eb451f8125db195b5de0f822263888/unsloth_zoo-2025.3.17.tar.gz
tar -zxf unsloth_zoo-2025.3.17.tar.gz
rm -rf unsloth_zoo unsloth_zoo-2025.3.17.tar.gz
mv unsloth_zoo-2025.3.17/unsloth_zoo .
rm -rf unsloth_zoo-2025.3.17
patch -p0 -u < unsloth_zoo.patch

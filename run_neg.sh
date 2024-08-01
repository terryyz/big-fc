BS=10
MODEL=deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct
BACKEND=vllm
TEMP=0.8
N_SAMPLES=10
NUM_GPU=2
if [[ $MODEL == *"/"* ]]; then
  ORG=$(echo $MODEL | cut -d'/' -f1)--
  BASE_MODEL=$(echo $MODEL | cut -d'/' -f2)
else
  ORG=""
  BASE_MODEL=$MODEL
fi

python synthesize_fc.py \
    --tp $NUM_GPU \
    --negative \
    --model $MODEL \
    --bs $BS \
    --temperature $TEMP \
    --n_samples $N_SAMPLES \
    --resume \
    --backend $BACKEND \
    --trust_remote_code
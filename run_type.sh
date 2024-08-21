BS=10
MODEL=meta-llama/Meta-Llama-3.1-70B-Instruct
BACKEND=vllm
TEMP=0.2
N_SAMPLES=10
NUM_GPU=8
if [[ $MODEL == *"/"* ]]; then
  ORG=$(echo $MODEL | cut -d'/' -f1)--
  BASE_MODEL=$(echo $MODEL | cut -d'/' -f2)
else
  ORG=""
  BASE_MODEL=$MODEL
fi

python infer_type.py \
    --tp $NUM_GPU \
    --model $MODEL \
    --bs $BS \
    --temperature $TEMP \
    --n_samples $N_SAMPLES \
    --resume \
    --backend $BACKEND \
    --trust_remote_code
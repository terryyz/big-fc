import os
import json
import argparse

from model_type import DecoderBase, make_model
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TextColumn,
    TimeElapsedColumn,
)
from utils import write_jsonl, load_api_schema, load_example

def codegen(
    model: DecoderBase,
    save_path: str,
    greedy=False,
    n_samples=1,
    id_range=None,
    resume=True,
):
    with Progress(
        TextColumn(f"Synthesize Type Annotation •" + "[progress.percentage]{task.percentage:>3.0f}%"),
        BarColumn(),
        MofNCompleteColumn(),
        TextColumn("•"),
        TimeElapsedColumn(),
    ) as p:
        
        # create save_path if it doesn't exist, e.g., a/b.jsonl
        dirname = os.path.dirname(save_path)
        if not os.path.exists(dirname) and dirname != "":
            os.makedirs(dirname)
        
        api_schemas = load_api_schema()
        data = load_example()
        for id_num, schema in enumerate(p.track(api_schemas)):
            task_id = schema["task_id"]
            api = schema["data"]
            api_type = api.pop("type", None)
            if api_type == "class":
                continue
            if id_range is not None:
                low, high = id_range
                if id_num < low or id_num >= high:
                    p.console.print(f"Skipping {id_num} as it is not in {id_range}")
                    continue

            # read the existing file if save_path exists
            if os.path.exists(save_path):
                with open(save_path, "r") as f:
                    existing_data = f.read().splitlines()
            
            log = f"Synthesis: {id_num} @ {model}"
            example = data[task_id]
            n_existing = 0

            if resume:
                if os.path.exists(save_path):
                    n_existing = len([1 for line in existing_data if json.loads(line)["id_num"] == id_num and
                                    json.loads(line)["task_id"] == task_id])
                else:
                    n_existing = 0
                if n_existing > 0:
                    log += f" (resuming from {n_existing})"

            nsamples = n_samples - n_existing
            p.console.print(log)

            sidx = n_samples - nsamples
            while sidx < n_samples:
                outputs = model.codegen(
                    api,
                    example,
                    do_sample=not greedy,
                    num_samples=n_samples - sidx,
                )
                assert outputs, "No outputs from model!"

                samples = [
                    dict(
                        id_num=id_num,
                        task_id=task_id,
                        api_name=api["name"],
                        synthesis=completion,
                    )
                    for id_num, completion in zip([id_num]*len(outputs), outputs)
                ]
                print(f"Generated {len(samples)} samples")
                write_jsonl(save_path, samples, append=True)
                sidx += len(outputs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, type=str)
    parser.add_argument("--save_path", default=None, type=str)
    parser.add_argument("--bs", default=1, type=int)
    parser.add_argument("--n_samples", default=1, type=int)
    parser.add_argument("--temperature", default=0.0, type=float)
    parser.add_argument("--greedy", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--id_range", nargs=2, type=int)
    parser.add_argument("--backend", default="vllm", type=str, choices=["vllm", "openai"])
    parser.add_argument("--base_url", default=None, type=str)
    parser.add_argument("--tp", default=1, type=int)
    parser.add_argument("--trust_remote_code", action="store_true")
    parser.add_argument("--tokenizer_legacy", action="store_true")
    parser.add_argument("--tokenizer_name", default=None, type=str)

    args = parser.parse_args()

    if args.greedy or (args.temperature == 0 and args.n_samples == 1):
        args.temperature = 0
        args.bs = 1
        args.n_samples = 1
        args.greedy = True
        print("Greedy decoding ON (--greedy): setting bs=1, n_samples=1, temperature=0")

    if args.id_range is not None:
        assert len(args.id_range) == 2, "id_range must be a list of length 2"
        assert args.id_range[0] < args.id_range[1], "id_range must be increasing"
        args.id_range = tuple(args.id_range)

    # Make dir for codes generated by each model
    model_runner = make_model(
        model=args.model,
        backend=args.backend,
        batch_size=args.bs,
        temperature=args.temperature,
        base_url=args.base_url,
        tp=args.tp,
        trust_remote_code=args.trust_remote_code,
        tokenizer_name=args.tokenizer_name,
        tokenizer_legacy=args.tokenizer_legacy
    )
    
    if not args.save_path:
        save_path = args.model.replace("/", "--") + f"--{args.backend}-{args.temperature}-{args.n_samples}.jsonl"
        save_path = "typeinfer--" + save_path
    else:
        save_path = args.save_path

    codegen(
        model=model_runner,
        save_path=save_path,
        greedy=args.greedy,
        n_samples=args.n_samples,
        resume=args.resume,
        id_range=args.id_range
    )


if __name__ == "__main__":
    main()

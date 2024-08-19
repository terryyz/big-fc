import json
import os
from abc import ABC, abstractmethod
from typing import List
from warnings import warn

import openai
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from constants import TYPE_INFERENCE_TEMPLATE, TYPE_SCHEMA, TYPE_RESPONSE_TEMPLATE

try:
    from vllm import LLM, SamplingParams
except ImportError:
    warn("VLLM decoder will not work. Fix by `pip install vllm`")

import openai_request

EOS = [
    "<|endoftext|>",
    "<|endofmask|>",
    "</s>",
]


# some random words which serves as the splitter
_MAGIC_SPLITTER_ = "-[[]]-this-is-really-our-highest-priority-[[]]-"


def make_chat_prompt(api: str, example: str, tokenizer: AutoTokenizer) -> str:
    prompt = TYPE_INFERENCE_TEMPLATE.format(api=api, example=example)
    response = TYPE_SCHEMA + "\n" + TYPE_RESPONSE_TEMPLATE.format(_MAGIC_SPLITTER_=_MAGIC_SPLITTER_, name=api["name"])
    prompt = tokenizer.apply_chat_template(
        [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": response},
        ],
        tokenize=False,
    ).split(_MAGIC_SPLITTER_)[0]
    return prompt


class DecoderBase(ABC):
    def __init__(
        self,
        name: str,
        batch_size: int = 1,
        temperature: float = 0.8,
        max_new_tokens: int = 1280,
        dtype: str = "bfloat16",  # default
        trust_remote_code: bool = False,
        tokenizer_name: str = None,
        tokenizer_legacy: bool = False,
    ) -> None:
        print("Initializing a decoder model: {} ...".format(name))
        self.name = name
        self.batch_size = batch_size
        self.temperature = temperature
        self.eos = EOS
        self.skip_special_tokens = False
        self.max_new_tokens = max_new_tokens
        self.dtype = dtype
        self.trust_remote_code = trust_remote_code
        self.tokenizer_name = tokenizer_name
        self.tokenizer_legacy = tokenizer_legacy

    @abstractmethod
    def codegen(
        self, api: str, example: str, do_sample: bool = True, num_samples: int = 200
    ) -> List[str]:
        pass

    @abstractmethod
    def is_direct_completion(self) -> bool:
        pass

    def __repr__(self) -> str:
        return self.name

    def __str__(self) -> str:
        return self.name


class VllmDecoder(DecoderBase):
    def __init__(self, name: str, tp: int, **kwargs) -> None:
        super().__init__(name, **kwargs)

        kwargs = {
            "tensor_parallel_size": int(os.getenv("VLLM_N_GPUS", tp)),
            "dtype": self.dtype,
            "trust_remote_code": self.trust_remote_code,
        }
        if self.tokenizer_name is None:
            self.tokenizer_name = self.name
        
        self.tokenizer = AutoTokenizer.from_pretrained(self.tokenizer_name, **kwargs, legacy=self.tokenizer_legacy)
        self.llm = LLM(model=name, max_model_len=8192, **kwargs)
        self.llm.set_tokenizer(tokenizer=self.tokenizer)

    def is_direct_completion(self) -> bool:
        return self.tokenizer.chat_template is None

    def codegen(
        self, prompt: str, do_sample: bool = True, num_samples: int = 200
    ) -> List[str]:
        if do_sample:
            assert self.temperature > 0, "Temperature must be greater than 0!"
        batch_size = min(self.batch_size, num_samples)

        vllm_outputs = self.llm.generate(
            [prompt] * batch_size,
            SamplingParams(
                temperature=self.temperature,
                max_tokens=self.max_new_tokens,
                top_p=0.95 if do_sample else 1.0,
                stop=self.eos,
            ),
            use_tqdm=False,
        )

        gen_strs = [x.outputs[0].text.replace("\t", "    ") for x in vllm_outputs]
        return gen_strs


class GeneralVllmDecoder(VllmDecoder):
    def __init__(self, name: str, **kwargs) -> None:
        super().__init__(name, **kwargs)
        self.eos += ["\n```\n"]
        print(f"EOS strings: {self.eos}")

    def codegen(
        self, api: str, example: str, do_sample: bool = True, num_samples: int = 200
    ) -> List[str]:
        prompt = make_chat_prompt(api, example, self.tokenizer)
        return VllmDecoder.codegen(self, prompt, do_sample, num_samples)


class OpenAIChatDecoder(DecoderBase):
    def __init__(self, name: str, base_url=None, **kwargs) -> None:
        super().__init__(name, **kwargs)
        self.client = openai.OpenAI(base_url=base_url)

    def codegen(
        self, api: str, example: str, do_sample: bool = True, num_samples: int = 200
    ) -> List[str]:
        if do_sample:
            assert self.temperature > 0, "Temperature must be positive for sampling"
        batch_size = min(self.batch_size, num_samples)

        # construct prompt
        fmt = "text"
        
        # message = POSITIVE_TEMPLATE.format(api=api, example=examplem) + "\n" + SCHEMA + RESPONSE_TEMPLATE.split("```json")[0]
        message = TYPE_INFERENCE_TEMPLATE.format(api=api, example=example) + "\n" + TYPE_SCHEMA + "\n" +  TYPE_RESPONSE_TEMPLATE.format(_MAGIC_SPLITTER_=_MAGIC_SPLITTER_, name=api["name"])
        ret = openai_request.make_auto_request(
            self.client,
            message=message,
            model=self.name,
            max_tokens=self.max_new_tokens,
            temperature=self.temperature,
            n=batch_size,
            response_format={"type": fmt},
        )

        outputs = []
        for item in ret.choices:
            content = item.message.content
            # if json serializable
            if fmt == "json_object":
                try:
                    json_data = json.loads(content)
                    # {"name": "", "signature": "", "short_description": ""}
                    if json_data.get("name", None) is not None:
                        outputs.append(json_data["name"])
                    else:
                        print(f"'name' field not found in: {json_data}")
                    if json_data.get("signature", None) is not None:
                        outputs.append(json_data["signature"])
                    if json_data.get("short_description", None) is not None:
                        outputs.append(json_data["short_description"])
                except Exception as e:
                    print(e)
            outputs.append(content)

        return outputs

    def is_direct_completion(self) -> bool:
        return False


def make_model(
    model: str,
    backend: str,
    batch_size: int = 1,
    temperature: float = 0.0,
    tp=1,
    base_url=None,
    trust_remote_code=False,
    tokenizer_name=None,
    tokenizer_legacy=True,
):
    if backend == "vllm":
        return GeneralVllmDecoder(
            name=model,
            batch_size=batch_size,
            temperature=temperature,
            tp=tp,
            trust_remote_code=trust_remote_code,
            tokenizer_name=tokenizer_name,
            tokenizer_legacy=tokenizer_legacy,
        )
    elif backend == "openai":
        return OpenAIChatDecoder(
            name=model,
            batch_size=batch_size,
            temperature=temperature,
            base_url=base_url,
        )

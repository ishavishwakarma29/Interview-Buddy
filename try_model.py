"""Chat with your trained InterviewBuddy in the terminal.

Run:  python try_model.py           (uses the trained model from model_path.txt)
      python try_model.py --base    (uses the untrained model, to compare)
Type 'quit' to stop.
"""
import json
import sys

import tinker
from dotenv import load_dotenv

from tinker_cookbook import model_info, renderers
from tinker_cookbook.tokenizer_utils import get_tokenizer

load_dotenv()

SYSTEM_PROMPT = json.loads(open("train.jsonl").readline())["messages"][0]["content"]
# Strip any memory notes so we start with the plain system prompt.
SYSTEM_PROMPT = SYSTEM_PROMPT.split("\n\nNotes from past sessions:")[0]


def main():
    info = json.load(open("model_path.txt"))
    service = tinker.ServiceClient()
    if "--base" in sys.argv:
        sampler = service.create_sampling_client(base_model=info["base_model"])
        print("(Using the UNTRAINED base model)")
    else:
        sampler = service.create_sampling_client(model_path=info["model_path"])

    renderer = renderers.get_renderer(
        model_info.get_recommended_renderer_name(info["base_model"]),
        get_tokenizer(info["base_model"]),
    )
    params = tinker.SamplingParams(max_tokens=400, temperature=0.7, stop=renderer.get_stop_sequences())

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    print("InterviewBuddy ready. Say hi to start. Type 'quit' to stop.\n")
    while True:
        text = input("You: ").strip()
        if text.lower() in {"quit", "exit"}:
            break
        messages.append({"role": "user", "content": text})
        out = sampler.sample(renderer.build_generation_prompt(messages), num_samples=1, sampling_params=params).result()
        reply, _ = renderer.parse_response(out.sequences[0].tokens)
        messages.append({"role": "assistant", "content": reply["content"]})
        print(f"\nInterviewBuddy: {renderers.get_text_content(reply)}\n")


if __name__ == "__main__":
    main()

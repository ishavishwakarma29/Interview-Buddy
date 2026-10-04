"""Teach an open-weight model to be InterviewBuddy, using train.jsonl.

Run:  python train.py
Needs TINKER_API_KEY in your .env file.
When it finishes, the trained model's address is saved in model_path.txt.
"""
import json
import logging
import os
import random

import tinker
from dotenv import load_dotenv

from tinker_cookbook import checkpoint_utils, model_info, renderers
from tinker_cookbook.hyperparam_utils import get_lr
from tinker_cookbook.supervised.common import compute_mean_nll
from tinker_cookbook.supervised.data import conversation_to_datum
from tinker_cookbook.tokenizer_utils import get_tokenizer

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(message)s")
logging.getLogger("httpx").setLevel(logging.WARN)
log = logging.getLogger(__name__)

# ---- Settings (safe defaults for a small budget) ----
MODEL_NAME = "Qwen/Qwen3-8B"  # small open model that already knows how to chat
EPOCHS = 5          # how many times the model reads the whole dataset
BATCH_SIZE = 16     # conversations per training step
LORA_RANK = 32      # size of the "add-on" we train (bigger = more capacity, more cost)
LOG_PATH = "logs"   # local folder where Tinker records checkpoints


def load(path):
    with open(path) as f:
        return [json.loads(line)["messages"] for line in f]


def main():
    tokenizer = get_tokenizer(MODEL_NAME)
    renderer_name = model_info.get_recommended_renderer_name(MODEL_NAME)
    renderer = renderers.get_renderer(renderer_name, tokenizer)

    train = load("train.jsonl")
    test = load("test.jsonl")
    # Only the interviewer's (assistant) turns are learned; the candidate's words are just context.
    to_datum = lambda convo: conversation_to_datum(
        convo, renderer, max_length=4096,
        train_on_what=renderers.TrainOnWhat.ALL_ASSISTANT_MESSAGES,
    )
    test_batch = [to_datum(c) for c in test]

    service = tinker.ServiceClient()
    trainer = service.create_lora_training_client(base_model=MODEL_NAME, rank=LORA_RANK)

    steps_per_epoch = len(train) // BATCH_SIZE
    total_steps = steps_per_epoch * EPOCHS
    base_lr = get_lr(MODEL_NAME)
    log.info(f"Training {MODEL_NAME} on {len(train)} conversations: {total_steps} steps, lr={base_lr:.2e}")

    random.seed(0)
    step = 0
    for epoch in range(EPOCHS):
        random.shuffle(train)
        for i in range(steps_per_epoch):
            batch = [to_datum(c) for c in train[i * BATCH_SIZE:(i + 1) * BATCH_SIZE]]
            lr = base_lr * (1 - step / total_steps)  # slowly lower the learning rate
            fwd = trainer.forward_backward(batch, loss_fn="cross_entropy")
            opt = trainer.optim_step(tinker.AdamParams(learning_rate=lr, beta1=0.9, beta2=0.95, eps=1e-8))
            result = fwd.result()
            opt.result()

            train_loss = compute_mean_nll(
                [x["logprobs"] for x in result.loss_fn_outputs],
                [d.loss_fn_inputs["weights"] for d in batch],
            )
            log.info(f"epoch {epoch + 1}/{EPOCHS}  step {step + 1}/{total_steps}  train_loss={train_loss:.3f}")
            step += 1

        # Score the held-back test set (no learning happens here): lower is better.
        test_out = trainer.forward(test_batch, loss_fn="cross_entropy").result()
        test_loss = compute_mean_nll(
            [x["logprobs"] for x in test_out.loss_fn_outputs],
            [d.loss_fn_inputs["weights"] for d in test_batch],
        )
        log.info(f"--- end of epoch {epoch + 1}: test_loss={test_loss:.3f} ---")
    os.makedirs(LOG_PATH, exist_ok=True)
    paths = checkpoint_utils.save_checkpoint(
        training_client=trainer,
        name="interviewbuddy-final",
        log_path=LOG_PATH,
        kind="sampler",
        loop_state={"epoch": EPOCHS},
        ttl_seconds=None,  # keep forever
    )
    with open("model_path.txt", "w") as f:
        json.dump({"model_path": paths["sampler_path"], "base_model": MODEL_NAME}, f)
    log.info(f"Done! Trained model saved at: {paths['sampler_path']} (also in model_path.txt)")


if __name__ == "__main__":
    main()

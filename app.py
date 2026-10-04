"""InterviewBuddy web app.

Brain:  your fine-tuned open model on Tinker (every chat turn).
Memory: Backboard (read once when a session starts, written once when it ends).

Run locally:  python app.py   then open http://localhost:5000
"""
import asyncio
import json
import os
import threading

import tinker
from backboard import BackboardClient
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from tinker_cookbook import model_info, renderers
from tinker_cookbook.tokenizer_utils import get_tokenizer

load_dotenv()
app = Flask(__name__)

# ---- The interviewer's instructions: exactly what the model was trained with ----
SYSTEM_PROMPT = json.loads(open("train.jsonl").readline())["messages"][0]["content"]
SYSTEM_PROMPT = SYSTEM_PROMPT.split("\n\nNotes from past sessions:")[0]
END_SESSION_MESSAGE = "Let's stop here. How did I do overall?"
MAX_NOTES = 3  # how many past-session notes to show the model

# ---- Tinker: load the trained model (model_path.txt, or env vars on Render) ----
if os.environ.get("MODEL_PATH"):
    MODEL_PATH, BASE_MODEL = os.environ["MODEL_PATH"], os.environ["BASE_MODEL"]
else:
    info = json.load(open("model_path.txt"))
    MODEL_PATH, BASE_MODEL = info["model_path"], info["base_model"]

sampler = tinker.ServiceClient().create_sampling_client(model_path=MODEL_PATH)
renderer = renderers.get_renderer(
    model_info.get_recommended_renderer_name(BASE_MODEL), get_tokenizer(BASE_MODEL)
)
SAMPLING = tinker.SamplingParams(max_tokens=400, temperature=0.7, stop=renderer.get_stop_sequences())

# ---- Backboard: one assistant holds your friend's memories ----
backboard = BackboardClient(api_key=os.environ["BACKBOARD_API_KEY"])

_loop = asyncio.get_event_loop()
threading.Thread(target=_loop.run_forever, daemon=True).start()

def run_async(coro):
    """Run an async function in the background, returning a Future."""
    return asyncio.run_coroutine_threadsafe(coro, _loop)

def get_assistant_id():
    """Use BACKBOARD_ASSISTANT_ID if set; otherwise create one assistant and save its ID to .env."""
    if os.environ.get("BACKBOARD_ASSISTANT_ID"):
        return os.environ["BACKBOARD_ASSISTANT_ID"]
    assistant = run_async(backboard.create_assistant(
        name="InterviewBuddy memory",
        description="Remembers one candidate's interview strengths and weak spots across sessions.",
    ))
    with open(".env", "a") as f:
        f.write(f"\nBACKBOARD_ASSISTANT_ID={assistant.assistant_id}\n")
    print(f"Created Backboard assistant {assistant.assistant_id} (saved to .env)")
    return str(assistant.assistant_id)


ASSISTANT_ID = get_assistant_id()


def ask_model(history, notes):
    """Send the conversation to the fine-tuned model and return its reply text."""
    system = SYSTEM_PROMPT + (f"\n\nNotes from past sessions: {notes}" if notes else "")
    messages = [{"role": "system", "content": system}] + history
    out = sampler.sample(renderer.build_generation_prompt(messages), num_samples=1, sampling_params=SAMPLING).result()
    reply, _ = renderer.parse_response(out.sequences[0].tokens)
    return renderers.get_text_content(reply)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/start", methods=["POST"])
def start():
    """Backboard read: fetch the most recent notes about this candidate."""
    memories = run_async(backboard.get_memories(ASSISTANT_ID)).memories
    memories.sort(key=lambda m: str(m.created_at or ""), reverse=True)
    notes = " ".join(m.content for m in memories[:MAX_NOTES])
    return jsonify({"notes": notes})


@app.route("/api/chat", methods=["POST"])
def chat():
    """One interview turn. No Backboard call here, so it costs only Tinker sampling."""
    body = request.json
    return jsonify({"reply": ask_model(body["history"], body.get("notes", ""))})


@app.route("/api/end", methods=["POST"])
def end():
    """The model writes a session summary; Backboard write saves it for next time."""
    body = request.json
    history = body["history"] + [{"role": "user", "content": END_SESSION_MESSAGE}]
    summary = ask_model(history, body.get("notes", ""))
    run_async(backboard.add_memory(ASSISTANT_ID, content=summary, metadata={"source": "session_summary"}))
    return jsonify({"summary": summary})


if __name__ == "__main__":
    app.run(port=int(os.environ.get("PORT", 5000)))  # no auto-reloader: it would create a second Backboard assistant

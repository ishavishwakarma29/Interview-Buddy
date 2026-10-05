# 🎤 InterviewBuddy

**A patient mock interviewer, fine-tuned on an open-weight model, that remembers what you struggle with.**

Built for the [Hacktoberfest Weekend Challenge: Build for a Friend](https://dev.to/challenges/hacktoberfest-weekend-2026-10-01). I made it for a friend preparing for software engineering interviews.

InterviewBuddy asks one question at a time and grades every answer in the same format:

```
What worked:      specific things you did well
To improve:       1–2 concrete fixes
Stronger version: your own story, retold better
Next question:    ...
```

When you're stuck, it gives a hint instead of the answer. When you're nervous, it slows down. When you end a session, it writes a summary of your strengths and weak spots. Next time, it uses that summary to pick questions that target your weak spots.

---

## How it works

```
Browser (chat page)
  ├─ Session start → Backboard: load notes from past sessions
  ├─ Every answer  → Qwen3-8B + my LoRA adapter (Tinker): feedback + next question
  └─ End session   → the model writes a summary → Backboard: save it
```

| Piece | Tool | Role |
|---|---|---|
| 🧠 Brain | **Qwen3-8B** + LoRA adapter, trained and served on **[Tinker](https://thinkingmachines.ai/tinker/)** | Runs the interview and writes the session summaries |
| 💾 Memory | **[Backboard](https://backboard.io)** | Remembers the candidate across sessions (2 calls per session) |
| 🌐 App | Flask + one HTML page | Chat UI |

**LoRA** trains a small add-on (an "adapter") instead of changing the whole model. That's how I taught Qwen3-8B a new behavior for a fraction of the cost.

---

## The training data

105 multi-turn mock-interview conversations: 95 for training and 10 held back for testing.

| Category | Conversations | Teaches |
|---|---|---|
| Behavioral | 30 | The STAR format and putting numbers on results |
| Technical concepts | 25 | Gently correcting factual mistakes |
| System design | 20 | Clarifying requirements before designing |
| Hard moments | 30 | "I don't know", nervousness, rambling, "just tell me the answer" |

- **153 graded feedback turns**
- **27 conversations** include *"Notes from past sessions"*, which teach the model to use its memory
- Training loss counts only on the interviewer's turns

---

## Project structure

```
interviewbuddy/
├── app.py               # Web server: Tinker model + Backboard memory
├── templates/index.html # Chat page
├── train.py             # Fine-tune Qwen3-8B with LoRA on Tinker
├── try_model.py         # Chat with the model in the terminal (--base = untrained)
├── list_models.py       # Show which models your Tinker account supports
├── build_dataset.py     # Validate + merge data into train/test files
├── train.jsonl          # 95 training conversations
├── test.jsonl           # 10 held-out conversations
├── data_parts/          # The 4 dataset batches + the scripts that generate them
└── requirements.txt
```

---
# Project Demo

[![Interview buddy demo](https://img.youtube.com/vi/G9_nsJ1eNF0/0.jpg)](https://www.youtube.com/watch?v=G9_nsJ1eNF0)

## Run it yourself

### 1. Install

```bash
git clone https://github.com/YOUR_USERNAME/interviewbuddy.git
cd interviewbuddy
python -m venv venv
```

Activate the environment:

```bash
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

Then install the packages:

```bash
pip install -r requirements.txt
```

### 2. Add your keys

Create a file named `.env`:

```
TINKER_API_KEY=your_tinker_key
BACKBOARD_API_KEY=your_backboard_key
```

### 3. (Optional) Rebuild the dataset

```bash
python build_dataset.py
```

### 4. Train

```bash
python train.py
```

Watch `train_loss` go down, and check `test_loss` after each epoch. When training finishes, the model's address is saved in `model_path.txt`.

### 5. Try it in the terminal

```bash
python try_model.py          # your fine-tuned interviewer
python try_model.py --base   # the untrained model, for comparison
```

### 6. Run the web app

```bash
python app.py
```

Open **http://localhost:5000**, say hi, and answer a few questions. Then click **End session** and reload the page: your notes from the session appear at the top.

The first time it runs, the app creates a Backboard assistant and adds `BACKBOARD_ASSISTANT_ID` to your `.env`. Keep that line, because it holds your memory.

---

## Make it your own

The interview type is set in the system prompt and the question topics. To retarget it (nursing, MBA, citizenship, language practice…):

1. Edit the generator scripts in `data_parts/` and re-run them.
2. Run `python build_dataset.py`.
3. Run `python train.py`.

Because the weights are open, the behavior is yours to change.

---

## Why open weights?

- **The behavior is trained into the model, not just prompted.** The format, the patience, and refusing to give answers away all come from training.
- **I own the adapter.** I can retrain it, swap it, or run it elsewhere, and no vendor can change it under me.
- **It's tailored to one person.** I add my friend's real sticking points to the data and retrain.
- **It's cheap.** The full fine-tune was about 150K tokens.

---

## Built with

[Qwen3-8B](https://huggingface.co/Qwen/Qwen3-8B) · [Tinker](https://thinkingmachines.ai/tinker/) · [Backboard](https://backboard.io) · [Flask](https://flask.palletsprojects.com/) · built with help from Claude Code

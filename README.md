🟥 RHCSA Training Platform

A gamified, extensible command-line training engine designed to reinforce real RHCSA (EX200) skills through interactive, replayable labs.

This project simulates a Red Hat-style shell environment and supports multi-level progression, dynamic scoring, and per-level leaderboards.

🎯 Project Goals

Reinforce RHCSA command-line muscle memory

Make repetitive labs replayable and competitive

Support dynamic level creation via JSON

Provide safe command execution

Be portable across Windows, macOS, and Linux

Require no external dependencies

🧠 Current Feature Set
✅ JSON-Based Level System

Levels stored in levels/*.json

Automatically creates a default level if none exist

Easily extensible without modifying Python code

✅ Safe Command Execution

Only whitelisted commands are allowed

No shell=True

Prevents arbitrary command execution

✅ Gamified Scoring System

Base points per correct answer

Attempt penalty

Hint penalty

Speed bonus

Streak bonus

Total score tracking

✅ Per-Level Leaderboards

Stored in highscores.json

Top 10 scores per level

Automatically migrates old leaderboard format

✅ Time Tracking

Per-step time bonus

Total level completion time recorded

Time displayed on leaderboard

✅ Cross-Platform Compatibility

Uses built-in Python libraries only

Windows/macOS/Linux compatible

Clear-screen handling works across platforms

📁 Project Structure
rhcsa_game.py
levels/
    cli_basics.json
highscores.json
README.md
▶️ Running the Program
python rhcsa_game.py

Main Menu:

1. Play Level
2. View Leaderboard
3. Exit
🧩 Level File Format

Levels are defined as JSON.

Example:

{
  "level_name": "CLI Basics",
  "description": "Fundamental shell commands",
  "steps": [
    {
      "id": "CLI-01",
      "prompt": "Display the current date and time.",
      "validator": "exact",
      "answer": "date",
      "hint": "Single command.",
      "explanation": "date shows system time."
    }
  ]
}
🛠 Validator Types

Each step supports:

"exact" → command must match exactly

"contains" → command must include substring

"starts_with" → command must start with value

🏆 Leaderboard Format

Leaderboard is stored as:

{
  "CLI Basics": [
    {
      "name": "Scott",
      "score": 540,
      "time": 38.21
    }
  ]
}

Legacy formats are automatically converted.

⏱ Scoring Model

Each step awards:

100 base points

−10 per incorrect attempt

−25 if hint used

+30 / +20 / +10 based on speed tier

+50 streak bonus (3+ consecutive correct)

Level completion time is recorded and shown in leaderboard.

🔒 Security Model

Only whitelisted commands are executed

No arbitrary shell access

No shell injection

No elevated privilege operations

🚀 Planned Features

Procedural permission labs (randomized chmod/chown scenarios)

Unlockable level progression

Difficulty selector

Full RHEL VM “lab mode”

Post-check grading system (CTF-style)

Randomized file/permission generation

Exam mode (no hints, strict timing)

🧱 Development Philosophy

Stable core loop before feature expansion

JSON-driven content for extensibility

Backward-compatible data migrations

Cross-platform compatibility first

Feature additions in isolated commits

💡 Vision

This project is evolving from a simple CLI script into a modular RHCSA training engine.

Future direction includes:

Fully randomized labs

Real filesystem validation

Linux VM integration

Procedural level generation

Competitive scoring system

Possibly a web interface

🧑‍💻 Author Notes

Built as a personal RHCSA training tool with iterative development, version control discipline, and progressive architectural refinement.

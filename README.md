# Mem0 GrowthOS

A growth intelligence platform built for Mem0's GTM team. It finds developers hitting the AI memory wall in real time and helps the team reach them with the right message before they build something custom and move on.

Live Demo: https://mem0-growthos.onrender.com

---

## The Problem This Solves

Mem0 fixes one of the most frustrating problems in AI development. Every AI app built today forgets everything the moment a conversation ends. Mem0 solves that with three lines of code.

But here is the catch. Thousands of developers are hitting this exact wall every single day on Reddit, GitHub and Stack Overflow. Most of them have never heard of Mem0. They spend days building their own memory systems from scratch, get frustrated, and move on.

This tool is built to reach those developers before that happens.

---

## How It Works

Open the app, click Scan Now, and the platform fills up with everything the team needs for the day.

**Signal Radar** shows developer pain points scored by urgency. The most critical ones are flagged so the team knows exactly who to reach out to first.

**Outreach Composer** generates three personalized response drafts for each signal, in helpful, technical and direct tones. The system reads what the developer actually said, figures out which specific problem they are facing, and picks the argument that fits. It does not generate generic responses.

**Content Command** produces a LinkedIn post, a Hacker News blog hook and a cold email to a startup CTO, all ready to use or edit. The team can regenerate any of them with a custom angle in one click.

**Insights** shows which failure modes are showing up most, which sources are most active and where the biggest gaps in current outreach are.

---

## Run It Yourself

Clone the repo and install dependencies:

```bash
git clone https://github.com/NiranjanTapasv1/Mem0-growthOS.git
cd Mem0-growthOS
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Add your Gemini API key to a .env file:

```
GEMINI_API_KEY=your_key_here
```

Get a free key at aistudio.google.com, no credit card needed.

Start the app:

```bash
python app.py
```

Open http://localhost:5000 and click Scan Now.

---

## Stack

Python and Flask on the backend. Vanilla HTML, CSS and JavaScript on the frontend. Google Gemini 2.0 Flash as the AI model. Deployed on Render.

---

## What Is Next

Right now the signals are AI generated simulations. The next version plugs in live Reddit scraping via PRAW and the GitHub Issues API so the feed pulls from real developer conversations happening today. After that, a feedback loop where the team marks responses as posted or ignored so the system learns what actually converts over time.

---

Built by Niranjan Tapasvi for the Basis Set Ventures AI Fellowship 2026

© 2026 Niranjan Tapasvi. All rights reserved.
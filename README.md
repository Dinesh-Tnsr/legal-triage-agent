# Legal Triage Graph: AI-Powered Legal Routing & Intake System

An autonomous, state-managed legal triage engine built on ADK 2.0 to accurately route civil disputes and critical criminal intakes. Submitted for the Kaggle AI Agents Capstone Project (Agents for Business Track).

## The Problem
Law firms and legal enterprises bleed capital manually sorting through top-of-funnel intake calls. Paralegals spend hours qualifying leads, dealing with out-of-scope queries, and filtering critical criminal emergencies from standard civil disputes. Furthermore, deploying standard LLMs for this task is a massive liability risk, as they frequently hallucinate and dispense unauthorised legal advice.

## The Solution
The Legal Triage Graph automates the intake pipeline whilst strictly enforcing compliance. It categorises queries into deterministic tracks, aggressively protects the firm from malpractice by refusing to give formal advice, and seamlessly escalates high-risk, high-value leads directly to a human attorney. 

### Core Architecture & Flow
The system utilises a graph-based routing architecture powered by Gemini 3.5 Flash and Google's Agent Development Kit (ADK 2.0). 

1. **Intake Shield (Start Node):** Analyzes the user's initial query and forces a rigid JSON categorization (Civil, Criminal, Out of Scope).
2. **Track-Specific Nodes:** 
   * **Civil Advisor:** Educates the user on standard procedures without providing legal counsel.
   * **Paralegal Intake (Criminal):** Triggers immediate emergency protocols, advising the user to remain silent until a public defender is assigned.
3. **Escalation Node (HITL):** A Human-In-The-Loop failsafe. If the routing confidence score drops below 80%, the AI halts and routes the transcript to a human lawyer.
4. **State Memory Management:** The graph explicitly wipes the `ctx.state` after terminal nodes to prevent memory contamination and conversation looping across sequential client queries.

## Technical Requirements
* Python 3.10+
* Google Gemini API Key
* `uv` package manager (recommended)
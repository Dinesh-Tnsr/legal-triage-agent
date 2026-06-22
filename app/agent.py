from pydantic import BaseModel, Field
from typing import Optional, Literal
from pathlib import Path
from google import genai
from google.adk.agents import LlmAgent
from google.adk.agents.context import Context
from google.adk.workflow import Workflow, START

class TriageState(BaseModel):
    user_query: str = Field(
        default="", 
        description="The original prompt typed by the client."
    )
    disclaimer_added: bool = Field(
        default=False, 
        description="Tracks if the strict legal disclaimer was injected."
    )
    category: Optional[str] = Field(
        default=None, 
        description="Strictly: 'civil', 'criminal', or 'out_of_scope'."
    )
    confidence_score: Optional[int] = Field(
        default=None, 
        description="Router's confidence score from 1 to 100."
    )
    intake_location: Optional[str] = Field(
        default=None, 
        description="Client's location gathered by the paralegal."
    )
    intake_charge: Optional[str] = Field(
        default=None, 
        description="Criminal charges gathered by the paralegal."
    )
    human_decision: Optional[str] = Field(
        default=None, 
        description="The final verdict from the human manager (Approve/Reject)."
    )

class TriageDeskOutput(BaseModel):
    reasoning: str
    confidence_score: int
    category: Literal["civil", "criminal", "out_of_scope"]

def intake_shield(node_input: str, ctx: Context) -> str:
    print("\n--- LEGAL DISCLAIMER ---")
    
    genai_client = genai.Client()
    prev_category = ctx.state.get('category')
    
    # 1. Handle Active Criminal Follow-Up
    if prev_category == 'criminal':
        ctx.state['intake_charge'] = node_input
        ctx.state['category'] = None  # WIPE MEMORY instantly to avoid loops
        ctx.route = 'escalation_node'
        return node_input
        
    ctx.state['user_query'] = node_input
    ctx.state['disclaimer_added'] = True

    # 2. Fresh Triage Evaluation
    try:
        response = genai_client.models.generate_content(
            model="gemini-3.5-flash",
            contents=node_input,
            config=dict(
                response_mime_type="application/json",
                response_schema=TriageDeskOutput,
                system_instruction=(
                    "You are a senior legal intake router. Analyse the user's situation and "
                    "categorise it strictly into civil, criminal, or out_of_scope. "
                    "In the response schema, confidence_score must be an integer from 1 to 100."
                )
            )
        )
        import json
        res_data = json.loads(response.text)
        category = res_data.get("category")
        confidence = res_data.get("confidence_score")
    except Exception as e:
        print(f"\n[!] API CRASH INTERCEPTED: {e}")
        # If the API crashes, reject the query. Do NOT trigger a fake legal escalation.
        ctx.state['category'] = None
        ctx.route = "out_of_scope"
        return node_input

    # 3. Secure Routing & Memory Management
    if not category or confidence is None or confidence < 80:
        ctx.state['category'] = None  # Wipe memory
        ctx.route = "escalation_node"
    elif category == "criminal":
        ctx.state['category'] = "criminal"  # KEEP MEMORY for the paralegal follow-up
        ctx.route = "criminal"
    elif category == "civil":
        ctx.state['category'] = None  # Wipe memory to prevent sticky civil loops
        ctx.route = "civil"
    elif category == "out_of_scope":
        ctx.state['category'] = None  # Wipe memory
        ctx.route = "out_of_scope"
    else:
        ctx.state['category'] = None  # Wipe memory
        ctx.route = "escalation_node"

    return node_input

def rejection_node(node_input: str) -> str:
    print("\n[!] QUERY REJECTED: OUT OF SCOPE")
    return "I am strictly a Legal Triage Assistant. I can only assist with legal queries. Your query is outside the scope of my capabilities."

civil_advisor = LlmAgent(
    name="CivilAdvisor",
    model="gemini-3.5-flash",
    instruction=(
        "You are a Civil Rights Advisor. Provide clear, general information regarding civil disputes. "
        "STRICT RULE: You must explicitly state that you are an AI providing educational information, "
        "not formal legal advice. Do not draft legal documents or ask for sensitive personal data. "
        "Keep responses structured, factual, and strictly under 150 words."
    )
)

rules_path = Path(__file__).resolve().parent / "criminal_intake.md"
with open(rules_path, "r", encoding="utf-8") as file:
    criminal_rules = file.read()

paralegal_intake = LlmAgent(
    name="ParalegalIntake",
    model="gemini-3.5-flash", 
    instruction=f"{criminal_rules}\nGather the location and charge, and do not offer legal advice."
)

def escalation_node(ctx: Context) -> str:
    print("\n========================================")
    print("!!! HUMAN-IN-THE-LOOP (HITL) HALT !!!")
    print("CRITICAL ESCALATION DETECTED.")
    print("========================================")
    
    ctx.state['human_decision'] = "PENDING"
    ctx.state['category'] = None
    ctx.state['confidence_score'] = None
    
    return "Your lawyer is on the way to you. Please remain silent and do not discuss the incident with anyone until your lawyer arrives."
app = Workflow(
    name="LegalTriageGraph",
    state_schema=TriageState,
    edges=[
        (START, intake_shield, {
            "criminal": paralegal_intake,
            "civil": civil_advisor,
            "out_of_scope": rejection_node,
            "escalation_node": escalation_node
        })
    ]
)

root_agent = app
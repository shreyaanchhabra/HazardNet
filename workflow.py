from typing import TypedDict
from groq import Groq
import base64, json
from prompts import *
from datetime import datetime
import requests, os

from langgraph.graph import END, START, StateGraph

groq_api_key = os.getenv('GROQ_API_KEY') 

# --- 1. THE STATE ---
class DisasterState(TypedDict):
    image_path: str          # Input
    disaster: dict          # Output of Step 1
    risk_level: str         # Output of Step 2
    action_plan: str        # Output of Step 3

# --- 2. THE AGENT CLASS ---
class DisasterResponseAgent:
    def __init__(self):
        self.workflow = self.build_workflow()

    def build_workflow(self) -> StateGraph:
        # Define the Graph
        workflow = StateGraph(DisasterState)

        # Add Nodes (Your 4 Specialists)
        workflow.add_node("detect", self.detect_node)
        workflow.add_node("risk", self.risk_node)
        workflow.add_node("plan", self.plan_node)
        workflow.add_node("send_to_n8n", self.send_to_n8n_node)

        # Connect them linearly
        workflow.add_edge(START, "detect")
        workflow.add_conditional_edges(
            "detect",
            self.should_continue,
            {
                "risk": "risk",
                "end": END
            }
        )
        workflow.add_edge("risk", "plan")
        workflow.add_edge("plan", "send_to_n8n")
        workflow.add_edge("send_to_n8n", END)

        return workflow.compile()

    # --- CONDITIONAL ROUTING FUNCTION ---
    def should_continue(self, state: DisasterState) -> str:
        disaster_type = state["disaster"]["type"]        
        if disaster_type.strip().lower() == "none":
            return "end"
        else:
            return "risk"
    
    # --- NODE IMPLEMENTATIONS ---
    # Function to encode the image
    def encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def call_llm(self, prompt: str) -> str: 
        from langchain_groq import ChatGroq
        llm = ChatGroq(
            model="openai/gpt-oss-120b",  # Check Groq console for latest models
            temperature=0,
            max_tokens=None,
            timeout=None,
            max_retries=2,
            api_key=groq_api_key # SanD Hacks
        )
        return llm.invoke(prompt).content

    def call_vision_llm(self, image_path: str, prompt: str):
        # Getting the base64 string
        base64_image = self.encode_image(image_path)
        client = Groq(api_key=groq_api_key)

        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                            },
                        },
                    ],
                }
            ],
            model="meta-llama/llama-4-maverick-17b-128e-instruct",
        )

        return chat_completion.choices[0].message.content

    def detect_node(self, state: DisasterState):
        """Step 1: Vision LLM"""
        detection_dict = json.loads(self.call_vision_llm(state["image_path"], disaster_detection_prompt).strip())
        return {"disaster": detection_dict}

    def risk_node(self, state: DisasterState):
        """Step 2: Risk Specialist"""
        risk_assessment_prompt_formatted = risk_assessment_prompt.format(disaster=json.dumps(state["disaster"]["description"]))
        model_risk_level = self.call_vision_llm(state["image_path"], risk_assessment_prompt_formatted)
        return {"risk_level": model_risk_level.strip()}

    def plan_node(self, state: DisasterState):
        """Step 3: Solutions Specialist"""
        action_plan_prompt_formatted = action_plan_prompt.format(disaster=json.dumps(state["disaster"]["description"]), risk_level=state["risk_level"])
        res = self.call_llm(action_plan_prompt_formatted)
        return {"action_plan": res.strip()}
    
    def send_to_n8n_node(self, state: DisasterState):
        import requests
        import markdown
        
        # Convert markdown action plan to HTML
        action_plan_html = markdown.markdown(
            state["action_plan"],
            extensions=['extra', 'nl2br']
        )

        # Create full HTML email
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ 
                    font-family: Arial, sans-serif; 
                    line-height: 1.6; 
                    color: #333; 
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                h1 {{ color: #d32f2f; border-bottom: 3px solid #d32f2f; padding-bottom: 10px; }}
                h2 {{ color: #1976d2; margin-top: 25px; }}
                h3 {{ color: #388e3c; }}
                .alert-header {{ 
                    background: #ffebee; 
                    padding: 20px; 
                    border-left: 5px solid #d32f2f;
                    margin-bottom: 20px;
                }}
                .info-box {{ 
                    background: #f5f5f5; 
                    padding: 15px; 
                    border-radius: 5px;
                    margin: 15px 0;
                }}
                .severity {{ 
                    font-weight: bold; 
                    font-size: 1.2em;
                    color: #d32f2f; 
                }}
                ul, ol {{ margin: 10px 0; padding-left: 25px; }}
                li {{ margin: 5px 0; }}
                strong {{ color: #1976d2; }}
            </style>
        </head>
        <body>
            <div class="alert-header">
                <h1>🚨 Crisis Alert Detected</h1>
            </div>
            
            <div class="info-box">
                <p><strong>Crisis Type:</strong> {state["disaster"]["type"]}</p>
                <p><strong>Description:</strong> {state["disaster"]["description"]}</p>
                <p class="severity">Severity Level: {state["risk_level"]}</p>
                <p><strong>Location:</strong> San Diego, California</p>
                <p><strong>Timestamp:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <h2>📋 Action Plan</h2>
            <div class="action-plan">
                {action_plan_html}
            </div>
        </body>
        </html>
        """
        
        payload = {
            "crisis_type": state["disaster"]["type"],
            "severity": state["risk_level"],
            "location": "San Diego, California",
            "email_html": full_html,  # This is the formatted HTML
            "action_plan": state["action_plan"],  # Keep raw markdown if needed
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            response = requests.post(
                "https://shreyaan.app.n8n.cloud/webhook/bb9073ab-16f5-4e52-9fa5-415a77a3fb62",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            print(f"✓ Sent to n8n - Status: {response.status_code}")
            print(f"Response: {response.text}")
            
        except Exception as e:
            print(f"✗ Error sending to n8n: {e}")
        
        return state  # Changed from {} to state


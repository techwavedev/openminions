#!/usr/bin/env python3
"""
Architect Wizard (Atlas)

Queries AGI's Qdrant index to retrieve relevant skills, agents, and templates based on the user's intent. 
Then uses `local_micro_agent` (or equivalent LLM) to dynamically build a phased execution pipeline (a Squad).

Usage:
    python3 execution/architect_wizard.py --intent "Write a blog post about AI trends and post to social media"
"""

import argparse
import sys
import json
import subprocess
import os

def call_local_agent(prompt):
    try:
        # We can route this to the local micro agent
        cmd = ["python3", "/Users/elton/code/agi/execution/local_micro_agent.py", "--task", prompt]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Agent warning: {result.stderr}", file=sys.stderr)
        return result.stdout.strip()
    except Exception as e:
        print(f"Agent execution failed: {e}", file=sys.stderr)
        return ""

def main():
    parser = argparse.ArgumentParser(description="Architect Wizard for Squad Design")
    parser.add_argument("--intent", required=True, help="Description of the squad goal in natural language")
    args = parser.parse_args()

    print(f"🏗️  Architect (Atlas) analyzing intent: '{args.intent}'")
    
    # 1. Consult Memory (Qdrant)
    print("🧠 Querying AGI Qdrant index for matching skills and agents...")
    sys.path.append("/Users/elton/code/agi/execution")
    try:
        from memory_manager import retrieve_context
        context_res = retrieve_context(args.intent, top_k=8, score_threshold=0.45, project="agi")
        chunks = context_res.get("chunks", [])
        if chunks:
            print(f"✅ Found {len(chunks)} relevant patterns in knowledge base.")
            context_texts = [f"- {c.get('content', '')}" for c in chunks]
            context_string = "\n".join(context_texts)
        else:
            print("⚠️ No strong matches found in Qdrant. Falling back to default heuristics.")
            context_string = "Use default multi-agent design patterns."
    except Exception as e:
        print(f"⚠️ Error querying memory: {e}. Falling back to default heuristics.")
        context_string = "Use default multi-agent design patterns."

    # 2. Design the Pipeline
    print("🎨 Designing Squad pipeline... (Invoking local LLM)")
    
    agent_prompt = f"""
    You are the Architect Agent (Atlas). Based on the user's intent: "{args.intent}"
    Design a JSON configuration for a 'Squad' composed of multiple specialized sub-agents.
    Use the following retrieved capabilities from our index to assign the best skills/tools:
    {context_string}
    
    Output ONLY a precise JSON in this format:
    {{
      "squad_name": "name-of-squad",
      "description": "Short description",
      "roles": [
         {{"name": "AgentName", "role": "Description", "tools": ["tool1", "tool2"]}}
      ],
      "pipeline_sequence": ["AgentName1"],
      "checkpoints": ["Description of checkpoint"]
    }}
    Do not output markdown code blocks. Output exactly the raw JSON.
    """
    
    design_str = call_local_agent(agent_prompt)
    
    try:
        if design_str.startswith("```json"):
            design_str = design_str[7:]
        if design_str.startswith("```"):
            design_str = design_str[3:]
        if design_str.endswith("```"):
            design_str = design_str[:-3]
        squad_design = json.loads(design_str.strip())
        print("\n✨ Squad Design Draft:")
        print(json.dumps(squad_design, indent=2))
        
        # 3. Output to data/squads
        squad_dir = os.path.join(os.getcwd(), "data", "squads", squad_design["squad_name"])
        os.makedirs(squad_dir, exist_ok=True)
        
        yaml_path = os.path.join(squad_dir, "squad.yaml")
        # Since pyyaml might not be installed for certain systems, fallback to json format if it fails
        try:
            import yaml
            with open(yaml_path, "w") as f:
                yaml.dump({"squad": squad_design}, f, sort_keys=False)
        except ImportError:
            with open(yaml_path.replace(".yaml", ".json"), "w") as f:
                json.dump({"squad": squad_design}, f, indent=2)
                
        print(f"✅ Design saved to {squad_dir}")
        print("Ready for human approval.")
        
    except json.JSONDecodeError:
        print("❌ Failed to parse Architect output as JSON.")
        print(f"Raw Output:\n{design_str}")
        sys.exit(1)

if __name__ == "__main__":
    main()

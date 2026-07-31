import os
import sys
import json
import urllib.request

def analyze_log(log_text):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable missing.")
        sys.exit(1)

    prompt = f"""
You are an expert DevOps AI Agent specializing in Kubernetes, Jenkins, Gradle, Spring Boot, SonarQube, and Trivy.
Analyze the following Jenkins pipeline failure log and provide a concise response.

Build Log Excerpt:
---
{log_text[-3000:]}
---

Respond ONLY in valid JSON with this structure:
{{
  "failure_category": "<BUILD_ERROR | SECURITY_TRIVY | QUALITY_GATE | K8S_DEPLOY>",
  "root_cause": "<One line clear summary of what failed>",
  "explanation": "<2-3 sentence technical explanation>",
  "suggested_fix": "<Step-by-step resolution or code diff>"
}}
"""

    payload = json.dumps({
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2
    }).encode('utf-8')

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
    )

    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            return res_data['choices'][0]['message']['content']
    except Exception as e:
        return f"Failed to consult AI Agent: {str(e)}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ai_analyst.py <path_to_console_log>")
        sys.exit(1)

    log_file_path = sys.argv[1]
    with open(log_file_path, "r", encoding="utf-8", errors="ignore") as f:
        log_content = f.read()

    result = analyze_log(log_content)
    print("\n" + "="*50)
    print("####### AI AGENT BUILD FAILURE DIAGNOSTIC ###########")
    print("="*50)
    print(result)
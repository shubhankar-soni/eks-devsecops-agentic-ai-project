import os
import sys
import json
import urllib.request
import urllib.error


def analyze_log(log_text):

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        print("Error: OPENAI_API_KEY environment variable missing.")
        sys.exit(1)

    # Jenkins automatically provides these environment variables
    job_name = os.getenv("JOB_NAME", "Unknown")
    build_number = os.getenv("BUILD_NUMBER", "Unknown")
    build_url = os.getenv("BUILD_URL", "Unknown")

    # Keep only the last part of the log to reduce token usage
    log_excerpt = log_text[-5000:]

    prompt = f"""
You are an expert DevOps AI Agent specializing in:

- Jenkins
- Kubernetes / EKS
- Gradle
- Spring Boot
- SonarQube
- Trivy
- Kaniko
- Docker

A Jenkins CI/CD pipeline has failed.

Job Name: {job_name}
Build Number: {build_number}
Build URL: {build_url}

Analyze the Jenkins log below and determine the actual reason the pipeline failed.

Jenkins Build Log:
------------------
{log_excerpt}
------------------

Respond ONLY with valid JSON.

Use this structure:

{{
  "failure_category": "<BUILD_ERROR | UNIT_TEST | SECURITY_TRIVY | QUALITY_GATE | CONTAINER_BUILD | K8S_DEPLOY | JENKINS_ERROR>",
  "failed_stage": "<pipeline stage that most likely failed>",
  "root_cause": "<clear one-line root cause>",
  "explanation": "<technical explanation of why the failure happened>",
  "suggested_fix": "<clear step-by-step solution>"
}}

Do not include markdown.
Do not include ```json.
Return only the JSON object.
"""

    payload = json.dumps({
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.2
    }).encode("utf-8")

    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        },
        method="POST"
    )

    try:

        with urllib.request.urlopen(request, timeout=60) as response:

            response_data = json.loads(
                response.read().decode("utf-8")
            )

            ai_response = response_data["choices"][0]["message"]["content"]

            # Verify that AI actually returned JSON
            diagnosis = json.loads(ai_response)

            return diagnosis

    except urllib.error.HTTPError as e:

        error_body = e.read().decode("utf-8", errors="ignore")

        print(f"OpenAI API HTTP Error: {e.code}")
        print(error_body)

        sys.exit(1)

    except urllib.error.URLError as e:

        print(f"Unable to connect to OpenAI API: {e}")
        sys.exit(1)

    except json.JSONDecodeError as e:

        print("AI Agent returned invalid JSON.")
        print(str(e))

        sys.exit(1)

    except Exception as e:

        print(f"AI Agent failed: {str(e)}")
        sys.exit(1)


def print_diagnosis(diagnosis):

    print("\n" + "=" * 60)
    print("AI AGENT BUILD FAILURE DIAGNOSTIC")
    print("=" * 60)

    print(f"\nFailure Category : {diagnosis.get('failure_category')}")
    print(f"Failed Stage     : {diagnosis.get('failed_stage')}")
    print(f"Root Cause       : {diagnosis.get('root_cause')}")

    print("\nExplanation:")
    print(diagnosis.get("explanation"))

    print("\nSuggested Fix:")
    print(diagnosis.get("suggested_fix"))

    print("\n" + "=" * 60)


if __name__ == "__main__":

    if len(sys.argv) < 2:

        print("Usage: python3 ai_analyst.py <console_log>")
        sys.exit(1)

    log_file_path = sys.argv[1]

    if not os.path.exists(log_file_path):

        print(f"Error: Log file does not exist: {log_file_path}")
        sys.exit(1)

    with open(
        log_file_path,
        "r",
        encoding="utf-8",
        errors="ignore"
    ) as log_file:

        log_content = log_file.read()

    diagnosis = analyze_log(log_content)

    # Save structured result for Jenkins/email
    with open(
        "ai_summary.json",
        "w",
        encoding="utf-8"
    ) as output_file:

        json.dump(
            diagnosis,
            output_file,
            indent=2
        )

    print_diagnosis(diagnosis)

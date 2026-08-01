
import os
import sys
import json
import urllib.request
import urllib.error


def analyze_log(log_text):


    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        print("Error: GEMINI_API_KEY environment variable missing.")
        sys.exit(1)

    job_name = os.getenv("JOB_NAME", "Unknown")
    build_number = os.getenv("BUILD_NUMBER", "Unknown")
    build_url = os.getenv("BUILD_URL", "Unknown")

    # Keep only the last 5000 characters to reduce token consumption
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

Analyze the Jenkins build log below and determine the actual reason
the pipeline failed.

Focus on:
1. Which pipeline stage failed
2. What caused the failure
3. Why the failure happened
4. How the DevOps engineer should fix it

Jenkins Build Log:
------------------
{log_excerpt}
------------------

Return the result using this JSON structure:

{{
  "failure_category": "<BUILD_ERROR | UNIT_TEST | SECURITY_TRIVY | QUALITY_GATE | CONTAINER_BUILD | K8S_DEPLOY | JENKINS_ERROR>",
  "failed_stage": "<pipeline stage that failed>",
  "root_cause": "<clear one-line root cause>",
  "explanation": "<technical explanation of why the failure happened>",
  "suggested_fix": "<clear step-by-step solution>"
}}

Return only the JSON object.
Do not include markdown.
Do not include ```json.
"""


    payload = json.dumps({
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json"
        }
    }).encode("utf-8")


    url = (
        "https://generativelanguage.googleapis.com/"
        "v1beta/models/gemini-2.5-flash:generateContent"
    )

    request = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key
        },
        method="POST"
    )

    try:

        print("Sending Jenkins failure log to Gemini AI Agent...")

        with urllib.request.urlopen(request, timeout=60) as response:

            response_data = json.loads(
                response.read().decode("utf-8")
            )


            ai_response = (
                response_data["candidates"][0]
                ["content"]["parts"][0]["text"]
            )


            diagnosis = json.loads(ai_response)

            return diagnosis

    except urllib.error.HTTPError as e:

        error_body = e.read().decode(
            "utf-8",
            errors="ignore"
        )

        print(f"Gemini API HTTP Error: {e.code}")
        print(error_body)

        sys.exit(1)

    except urllib.error.URLError as e:

        print(f"Unable to connect to Gemini API: {e}")

        sys.exit(1)

    except json.JSONDecodeError as e:

        print("Gemini returned invalid JSON.")
        print(f"JSON Error: {e}")

        sys.exit(1)

    except KeyError as e:

        print("Unexpected response received from Gemini API.")
        print(f"Missing response field: {e}")

        sys.exit(1)

    except Exception as e:

        print(f"AI Agent failed: {str(e)}")

        sys.exit(1)


def save_diagnosis(diagnosis):


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


def print_diagnosis(diagnosis):

    print("\n" + "=" * 60)
    print("AI AGENT BUILD FAILURE DIAGNOSTIC")
    print("=" * 60)

    print(
        f"\nFailure Category : "
        f"{diagnosis.get('failure_category', 'Unknown')}"
    )

    print(
        f"Failed Stage     : "
        f"{diagnosis.get('failed_stage', 'Unknown')}"
    )

    print(
        f"Root Cause       : "
        f"{diagnosis.get('root_cause', 'Unknown')}"
    )

    print("\nExplanation:")
    print(
        diagnosis.get(
            "explanation",
            "No explanation provided."
        )
    )

    print("\nSuggested Fix:")
    print(
        diagnosis.get(
            "suggested_fix",
            "No suggested fix provided."
        )
    )

    print("\n" + "=" * 60)


def main():

    if len(sys.argv) < 2:

        print(
            "Usage: python3 ai_analyst.py "
            "<path_to_console_log>"
        )

        sys.exit(1)

    log_file_path = sys.argv[1]


    if not os.path.exists(log_file_path):

        print(
            f"Error: Log file does not exist: "
            f"{log_file_path}"
        )

        sys.exit(1)

    print(f"Reading Jenkins log: {log_file_path}")


    with open(
        log_file_path,
        "r",
        encoding="utf-8",
        errors="ignore"
    ) as log_file:

        log_content = log_file.read()

    if not log_content.strip():

        print("Error: Jenkins console log is empty.")
        sys.exit(1)


    diagnosis = analyze_log(log_content)


    save_diagnosis(diagnosis)


    print_diagnosis(diagnosis)

    print("\nAI diagnosis saved to ai_summary.json")


if __name__ == "__main__":
    main()

import os
import sys
import json
import urllib.request
import urllib.error


def extract_failure_context(log_text):
    """
    Extract relevant error sections from the Jenkins console log
    instead of sending only the last few thousand characters.
    """

    error_keywords = [
        "Error from server",
        "script returned exit code",
        "BUILD FAILED",
        "FAILURE:",
        "FAILED",
        "Exception",
        "ImagePullBackOff",
        "ErrImagePull",
        "CrashLoopBackOff",
        "NotFound",
        "Forbidden",
        "Unauthorized",
        "Quality gate",
        "CRITICAL",
        "permission denied",
        "Operation not permitted",
        "connection refused",
        "timed out",
        "timeout"
    ]

    lines = log_text.splitlines()
    error_sections = []

    for i, line in enumerate(lines):

        for keyword in error_keywords:

            if keyword.lower() in line.lower():

                # Capture 25 lines before and 10 lines after the error
                start = max(0, i - 25)
                end = min(len(lines), i + 11)

                section = "\n".join(lines[start:end])

                error_sections.append(section)

                break

    if error_sections:

        combined_context = (
            "\n\n--- ERROR CONTEXT ---\n\n"
        ).join(error_sections)

        # Limit amount of data sent to Gemini
        return combined_context[-15000:]

    # Fallback if no known error pattern is found
    return log_text[-10000:]


def analyze_log(log_text):

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        print(
            "Error: GEMINI_API_KEY environment variable missing."
        )
        sys.exit(1)

    # Jenkins automatically provides these environment variables
    job_name = os.getenv("JOB_NAME", "Unknown")
    build_number = os.getenv("BUILD_NUMBER", "Unknown")
    build_url = os.getenv("BUILD_URL", "Unknown")

    # Extract relevant failure information
    log_excerpt = extract_failure_context(log_text)

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

Your task is to identify the ORIGINAL reason the pipeline failed.

IMPORTANT RULES:

1. Identify the ORIGINAL pipeline failure.

2. Do NOT treat errors occurring inside Jenkins post/failure
   handlers as the original build failure.

3. Prioritize failures from actual CI/CD stages such as:
   - Source Checkout
   - Unit Test & Coverage
   - SonarQube Analysis
   - SonarQube Quality Gate
   - Container Build & Push
   - Trivy Security Scan
   - Kubernetes / EKS Deployment

4. Use evidence from the Jenkins log.

5. Do not assume authentication, Kubernetes, Jenkins, Gradle,
   SonarQube, security, or permission problems unless the
   provided log contains evidence for them.

6. If a command returns a non-zero exit code, identify the
   command and the error immediately preceding that failure.

7. Distinguish the original pipeline failure from secondary
   failures caused by diagnostic or post-build steps.

Jenkins Failure Log Context:
----------------------------

{log_excerpt}

----------------------------

Analyze the failure and return ONLY valid JSON using exactly
this structure:

{{
  "failure_category": "<BUILD_ERROR | UNIT_TEST | SECURITY_TRIVY | QUALITY_GATE | CONTAINER_BUILD | K8S_DEPLOY | JENKINS_ERROR>",
  "failed_stage": "<pipeline stage that originally failed>",
  "root_cause": "<clear one-line description of the original root cause>",
  "explanation": "<technical explanation based on evidence from the log>",
  "suggested_fix": "<clear step-by-step solution>"
}}

Return only the JSON object.

Do not include markdown.

Do not include ```json.

Do not invent errors that are not present in the log.
"""

    # Gemini API request
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
            "responseMimeType": "application/json"
        }
    }).encode("utf-8")

    # Gemini API endpoint
    url = (
        "https://generativelanguage.googleapis.com/"
        "v1beta/models/gemini-3.5-flash-lite:generateContent"
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

        print(
            "Sending Jenkins failure context "
            "to Gemini AI Agent..."
        )

        with urllib.request.urlopen(
            request,
            timeout=60
        ) as response:

            response_data = json.loads(
                response.read().decode("utf-8")
            )

            # Extract Gemini response
            ai_response = (
                response_data["candidates"][0]
                ["content"]["parts"][0]["text"]
            )

            # Convert Gemini response into Python dictionary
            diagnosis = json.loads(ai_response)

            return diagnosis

    except urllib.error.HTTPError as e:

        error_body = e.read().decode(
            "utf-8",
            errors="ignore"
        )

        print(
            f"Gemini API HTTP Error: {e.code}"
        )

        print(error_body)

        sys.exit(1)

    except urllib.error.URLError as e:

        print(
            f"Unable to connect to Gemini API: {e}"
        )

        sys.exit(1)

    except json.JSONDecodeError as e:

        print(
            "Gemini returned invalid JSON."
        )

        print(
            f"JSON Error: {e}"
        )

        sys.exit(1)

    except KeyError as e:

        print(
            "Unexpected response received "
            "from Gemini API."
        )

        print(
            f"Missing response field: {e}"
        )

        sys.exit(1)

    except Exception as e:

        print(
            f"AI Agent failed: {str(e)}"
        )

        sys.exit(1)


def validate_diagnosis(diagnosis):
    """
    Verify that Gemini returned all required fields.
    """

    required_fields = [
        "failure_category",
        "failed_stage",
        "root_cause",
        "explanation",
        "suggested_fix"
    ]

    missing_fields = []

    for field in required_fields:

        if field not in diagnosis:

            missing_fields.append(field)

    if missing_fields:

        print(
            "Warning: Gemini response is missing "
            "expected fields:"
        )

        print(
            ", ".join(missing_fields)
        )


def save_diagnosis(diagnosis):
    """
    Save Gemini diagnosis to JSON file.
    Jenkins/email can use this file later.
    """

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
    """
    Print human-readable diagnosis to Jenkins console.
    """

    print("\n" + "=" * 60)

    print(
        "AI AGENT BUILD FAILURE DIAGNOSTIC"
    )

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

    # Verify that console log exists
    if not os.path.exists(log_file_path):

        print(
            f"Error: Log file does not exist: "
            f"{log_file_path}"
        )

        sys.exit(1)

    print(
        f"Reading Jenkins log: "
        f"{log_file_path}"
    )

    # Read Jenkins console log
    with open(
        log_file_path,
        "r",
        encoding="utf-8",
        errors="ignore"
    ) as log_file:

        log_content = log_file.read()

    if not log_content.strip():

        print(
            "Error: Jenkins console log is empty."
        )

        sys.exit(1)

    print(
        f"Jenkins log size: "
        f"{len(log_content)} characters"
    )

    # Show how much useful failure context was extracted
    failure_context = extract_failure_context(
        log_content
    )

    print(
        f"Extracted failure context: "
        f"{len(failure_context)} characters"
    )

    # Send Jenkins failure information to Gemini
    diagnosis = analyze_log(
        log_content
    )

    # Validate Gemini response
    validate_diagnosis(
        diagnosis
    )

    # Save result as JSON
    save_diagnosis(
        diagnosis
    )

    # Print readable result
    print_diagnosis(
        diagnosis
    )

    print(
        "\nAI diagnosis saved to "
        "ai_summary.json"
    )


if __name__ == "__main__":
    main()

import json
import re
import ollama
from config import LLM_MODEL

THRESHOLD = 0.20

# ✅ Simple greeting whitelist
GREETINGS = {
    "hi", "hello", "hey", "hii", "hiii",
    "good morning", "good afternoon", "good evening",
    "namaste", "hola"
}

def validate_hr_question(user_message: str) -> dict:
    """
    Uses Qwen 2.5B via Ollama to classify HR vs NON_HR.
    Allows greetings and all HR domains.
    Prints raw and parsed results to terminal.
    """

    # ---------------- FAST-PATH: GREETINGS ----------------
    normalized = user_message.lower().strip()

    if any(greet in normalized for greet in GREETINGS):
        result = {
            "is_hr": True,
            "label": "HR",
            "confidence": 0.99
        }

        print("\n--- GREETING AUTO-APPROVED ---")
        print(result)
        print("-----------------------------\n")

        return result

    # ---------------- LLM PROMPT ----------------
    prompt = f"""
You are an enterprise HR intent classifier.

Task:
Determine whether the message is related to Human Resources (HR).

HR INCLUDES (but is not limited to):

1. Employee Lifecycle
- Onboarding, Offboarding, Probation, Confirmation
- Notice period, Exit interview, Employee ID
- Full-time, Part-time, Contract, Intern

2. Recruitment & Hiring
- Job description, Resume, Interview
- Offer letter, CTC, DOJ, BGV, ATS
- Hiring manager, Talent acquisition

3. Payroll & Compensation
- Salary, Payslip, Bonus, Incentives
- Gross/Net salary, HRA, Allowances
- Reimbursement, Arrears, Payroll cycle

4. Statutory & Compliance (India)
- PF, ESI, PT, Gratuity
- TDS, UAN, Form 16
- Labor laws, Shops & Establishment

5. Leave & Attendance
- Leave policy, CL, SL, EL, PL
- Maternity / Paternity leave
- LOP, WFH, Attendance, Timesheet

6. Performance & Growth
- KPI, KRA, Appraisal, Promotion
- Increment, PIP, OKR
- Training, L&D

7. Company Policy & Culture
- HR policy, Code of conduct
- POSH, Grievance, Whistleblower
- Anti-harassment, Equal opportunity

8. Separation & Exit
- Resignation, Termination
- Relieving letter, Experience letter
- Full & Final settlement, NOC

9. HR Metrics
- Attrition, Retention, Headcount
- Time to hire, Engagement, D&I

10. HR Copilot Actions
- Apply leave
- Download payslip
- Show CTC breakup
- Explain PF deduction
- Generate offer letter
- Start onboarding
- Appraisal cycle queries

Also consider greetings (hi, hello, good morning) as HR-related.

Respond ONLY in valid JSON.
Do NOT add explanations.

JSON format:
{{
  "label": "HR" or "NON_HR",
  "confidence": number between 0 and 1
}}

Message:
"{user_message}"
"""

    # ---------------- LLM CALL ----------------
    try:
        response = ollama.chat(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        text = response["message"]["content"].strip()

        print("\n--- QWEN RAW RESPONSE ---")
        print(text)

    except Exception as e:
        print("\n--- QWEN ERROR ---")
        print(e)
        return {
            "is_hr": False,
            "label": "NON_HR",
            "confidence": 0.0
        }

    # ---------------- JSON EXTRACTION ----------------
    try:
        json_text = re.search(r"\{.*\}", text, re.S).group()

        print("\n--- EXTRACTED JSON ---")
        print(json_text)

        result = json.loads(json_text)

    except Exception as e:
        print("\n--- JSON PARSE ERROR ---")
        print(e)
        return {
            "is_hr": False,
            "label": "NON_HR",
            "confidence": 0.0
        }

    label = result.get("label", "NON_HR")
    confidence = float(result.get("confidence", 0.0))

    final_result = {
        "is_hr": label == "HR" and confidence >= THRESHOLD,
        "label": label,
        "confidence": confidence
    }

    print("\n--- FINAL VALIDATION RESULT ---")
    print(final_result)
    print("-------------------------------\n")

    return final_result

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
 
TASK:
Classify if the user message is HR-related or not.
 
HR SCOPE INCLUDES:
 
1. Employee Lifecycle
   Onboarding, offboarding, probation, confirmation, notice period, exit interview, employee ID (Emp ID), FTE (Full-Time Employee), part-time employee, contractual/temporary employee, intern/trainee
 
2. Recruitment & Hiring
   JD (Job Description), job posting/vacancy, applicant/candidate, resume/CV (Curriculum Vitae), shortlisting, screening, interviews (HR/technical/managerial), offer letter, CTC (Cost to Company), DOJ (Date of Joining), BGV (Background Verification), reference check, hiring manager, TA (Talent Acquisition), ATS (Applicant Tracking System)
 
3. Payroll & Compensation
   Salary/wages, CTC (Cost to Company), gross salary, net salary (take-home), basic pay, HRA (House Rent Allowance), special allowance, bonus, incentives, variable pay, payslip, payroll processing, salary cycle, reimbursement, arrears
 
4. Statutory & Compliance (India-specific)
   PF (Provident Fund), ESI (Employee State Insurance), PT (Professional Tax), gratuity, TDS (Tax Deducted at Source), UAN (Universal Account Number), Form 16, Form 12B/12BB, labor law compliance, Shops & Establishment Act
 
5. Leave & Attendance
   Leave policy, CL (Casual Leave), SL (Sick Leave), EL (Earned Leave)/PL (Privilege Leave), elective/optional leave, paid leave, maternity/paternity leave, comp-off (Compensatory Off), LOP (Loss of Pay), WFH (Work From Home), attendance regularization, biometric attendance, timesheet
 
6. Performance & Growth
   KPI (Key Performance Indicator), KRA (Key Result Area), performance appraisal, increment/hike, promotion, 360-degree feedback, PIP (Performance Improvement Plan), goal setting, OKR (Objectives and Key Results), L&D (Learning & Development), training programs
 
7. Company Policy & Culture
   Code of conduct, HR policy, POSH (Prevention of Sexual Harassment) policy, disciplinary action, grievance redressal, whistleblower policy, anti-harassment policy, equal opportunity policy
 
8. Separation & Exit
   Resignation, termination, layoff/retrenchment, absconding, relieving letter, experience letter, FNF (Full & Final Settlement), clearance process/NOC (No Objection Certificate)
 
9. HR Metrics & Analytics
   Attrition rate, retention rate, headcount, time to hire, cost per hire, employee engagement, absenteeism rate, D&I (Diversity & Inclusion)
 
10. Common HR Queries & Actions
    Leave balance check, apply for leave, download payslip, CTC breakup, explain PF/ESI/TDS deductions, generate offer/experience/relieving letters, start onboarding process, appraisal cycle queries, attendance regularization
 
CLASSIFICATION RULES:
- Greetings (hi, hello, good morning, namaste, etc.) → HR
- Employee wellness, benefits, work-life balance, policies → HR
- IT support, technical issues, facilities, non-HR admin → NON_HR
- When uncertain but employee-facing, favor HR classification
 
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

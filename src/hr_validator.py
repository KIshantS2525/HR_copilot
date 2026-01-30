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
Determine whether the user message is a question or concern that should be handled by the Human Resources (HR) department.

PRIMARY DECISION RULE (MANDATORY):
Classify a message as HR ONLY IF:
- It requires HR policy interpretation, HR approval, HR intervention, or HR-owned processes
- OR it relates to employee rights, employment terms, compensation, compliance, workplace safety, ethics, or wellbeing
- OR it involves sensitive people matters that require confidentiality or formal escalation

Classify a message as NON_HR IF:
- It can be handled by a manager, team lead, project manager, business analyst, event organizer, IT, or self-learning
- It is about projects, products, customers, delivery, technology, learning, or general curiosity

HR SCOPE INCLUDES:

1. Employee Lifecycle  
   Onboarding, offboarding, probation, confirmation, notice period, exit interview, employee ID (Emp ID – Employee Identification Number),  
   FTE (Full-Time Employee), part-time employee, contractual/temporary employee, intern/trainee

2. Recruitment & Hiring  
   JD (Job Description), job posting/vacancy, applicant/candidate, resume/CV (Curriculum Vitae), shortlisting, screening, interviews,  
   offer letter, CTC (Cost to Company), DOJ (Date of Joining),  
   BGV (Background Verification), reference check,  
   TA (Talent Acquisition), ATS (Applicant Tracking System)

3. Payroll & Compensation  
   Salary, wages, CTC (Cost to Company), gross salary, net salary,  
   basic pay, HRA (House Rent Allowance), allowances, bonus, incentives,  
   variable pay, payslip, payroll cycle, reimbursement, arrears

4. Statutory & Compliance (India-specific)  
   PF (Provident Fund),  
   ESI (Employee State Insurance),  
   PT (Professional Tax),  
   gratuity,  
   TDS (Tax Deducted at Source),  
   UAN (Universal Account Number),  
   Form 16 (Income Tax Certificate),  
   Form 12B / 12BB (Employee Tax Declaration Forms),  
   labor law compliance, Shops & Establishment Act

5. Leave & Attendance  
   Leave policy,  
   CL (Casual Leave),  
   SL (Sick Leave),  
   EL/PL (Earned Leave / Privilege Leave),  
   paid leave, maternity/paternity leave,  
   comp-off (Compensatory Off),  
   LOP (Loss of Pay),  
   WFH (Work From Home),  
   attendance regularization, biometric attendance, timesheet

6. Performance & Growth  
   KPI (Key Performance Indicator),  
   KRA (Key Result Area),  
   performance appraisal, increment/hike, promotion, feedback,  
   PIP (Performance Improvement Plan),  
   OKR (Objectives and Key Results),  
   L&D (Learning and Development), training programs

7. Company Policy & Culture  
   Code of conduct, HR policy,  
   POSH policy (Prevention of Sexual Harassment),  
   disciplinary action, grievance redressal, whistleblower policy,  
   anti-harassment, equal opportunity

8. Separation & Exit  
   Resignation, termination, layoff, retrenchment, absconding,  
   relieving letter, experience letter,  
   FNF settlement (Full and Final Settlement),  
   clearance/NOC (No Objection Certificate)

9. HR Metrics & Analytics  
   Attrition, retention, headcount,  
   time to hire, cost per hire,  
   engagement, absenteeism,  
   D&I (Diversity and Inclusion)

10. Common HR Queries & Actions  
    Leave balance, apply for leave, download payslip,  
    CTC breakup (Cost to Company breakup),  
    PF/ESI/TDS explanation (Provident Fund / Employee State Insurance / Tax Deducted at Source),  
    offer/experience letters, onboarding, appraisal cycle, attendance issues

11. Employee Wellbeing, Safety & Workplace Concerns  
    Workplace discomfort, harassment, discrimination, intimidation  
    Feeling unsafe or uncomfortable with manager or team  
    Excessive workload or after-office-hours expectations  
    Boundary violations, mental stress, burnout  
    Conflict requiring HR mediation or escalation

ALWAYS NON_HR (HARD REJECTION):
- Math or logic questions (e.g., "2+2")
- Programming or technical help (e.g., "write Python code", "debug error")
- Project timelines, delivery status, or task tracking
- Product, business, or customer requirement discussions
- Company events, fests, clubs, sports, dance, volunteering participation
- Learning resources, certifications, tutorials
- General company news not involving HR policy

CLASSIFICATION RULES:
- Greetings (hi, hello, good morning, namaste, etc.) → HR
- Employee wellness, benefits, work-life balance, or safety → HR
- IT support, technical issues, facilities, admin (non-HR) → NON_HR
- If the message does NOT clearly require HR authority or policy → NON_HR

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

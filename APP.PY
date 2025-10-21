
# pip install gradio transformers python-docx
'''
import gradio as gr
from transformers import AutoTokenizer, AutoModelForCausalLM
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import re
import os
import time

# --- MOCK DATABASE AND STATE ---
USER_DB = {
    "test_hr": {"password": "hr_password", "role": "hr"},
    "test_student": {"password": "student_password", "role": "student"}
}
JOB_POSTINGS = {} 

# --- MOCK IMPLEMENTATION DEFINITION ---
def generate_llm_output(prompt):
    """Generates a structured mock AI response."""
    name_match = re.search(r"Name: (.*)", prompt)
    skills_match = re.search(r"Skills: (.*)", prompt)
    name = name_match.group(1).strip() if name_match else "Applicant Name"
    skills = skills_match.group(1).strip() if skills_match else "Python, Leadership, SQL"
    
    return f"***DUMMY AI RESPONSE***\n\n**SUMMARY:** Highly motivated individual ({name}) with a strong foundation in {skills}. Proven ability to tackle complex challenges and drive results.\n\n**SKILLS:** {skills}\n\n**EXPERIENCE:** Simulated job experience here, demonstrating proficiency in key skills.\n\n**EDUCATION:** University details here."

class MockModel:
    def generate(self, input_ids, max_new_tokens, num_return_sequences):
        # In mock mode, we just return the input text (prompt) for the tokenizer to decode
        return {"input_ids": input_ids} 

class MockTokenizer:
    def __init__(self): self.eos_token = ""
    def __call__(self, text, *args, **kwargs): return {"input_ids": text}
    def decode(self, tokens, skip_special_tokens=True): 
        if isinstance(tokens, dict) and "input_ids" in tokens:
            tokens = tokens["input_ids"]
        if isinstance(tokens, str):
            return generate_llm_output(tokens)
        return generate_llm_output("Default Name: Default, Skills: Default")


# --- IBM Granite Model Loading (FIXED: MOCK FALLBACK ENSURED) ---

tokenizer = None
model = None

try:
    # Attempt to load the real model (will likely fail, triggering the mock)
    # This block MUST remain here as per the required architecture.
    tokenizer = AutoTokenizer.from_pretrained("ibm-granite/granite-3.3-2b-instruct")
    model = AutoModelForCausalLM.from_pretrained("ibm-granite/granite-3.3-2b-instruct")
    print("SUCCESS: Loaded IBM Granite model.")
except Exception as e:
    print(f"Warning: Could not load Granite model. Using DUMMY/MOCK function. Error: {e}")
    # CRITICAL FIX: Assign mock objects to global variables
    model = MockModel()
    tokenizer = MockTokenizer()


# --- AUTHENTICATION FUNCTIONS (UNCHANGED) ---

def register_user(username, password, role):
    if not username or not password or not role:
        return "❌ Registration failed: All fields are required.", gr.update(value=""), gr.update(value=""), gr.update(value=None), gr.update(value=""), gr.update(value="")
               
    username = username.strip()
    password = password.strip()
    
    if username in USER_DB:
        return f"❌ Registration failed: User '{username}' already exists.", gr.update(value=""), gr.update(value=""), gr.update(value=None), gr.update(value=""), gr.update(value="")
    
    USER_DB[username] = {"password": password, "role": role}
    
    return f"✅ Success! User '{username}' registered as **{role.upper()}**. Please proceed to the Login section.", gr.update(value=""), gr.update(value=""), gr.update(value=None), gr.update(value=""), gr.update(value="")


def user_login(username, password):
    username = username.strip()
    password = password.strip()
    
    if username in USER_DB:
        if USER_DB[username]["password"] == password:
            role = USER_DB[username]["role"]
            
            if role == "student":
                return (username, role), f"✅ Login Success! Welcome, {username} ({role.upper()}).", gr.update(visible=True), gr.update(visible=False), gr.update(visible=False)
            elif role == "hr":
                return (username, role), f"✅ Login Success! Welcome, {username} ({role.upper()}).", gr.update(visible=False), gr.update(visible=True), gr.update(visible=False)
        else:
            return (None, "guest"), "❌ Login Failed: Invalid password.", gr.update(visible=False), gr.update(visible=False), gr.update(visible=True)
    else:
        return (None, "guest"), "❌ Login Failed: Invalid username or password.", gr.update(visible=False), gr.update(visible=False), gr.update(visible=True)

def user_logout():
    return (None, "guest"), "👋 Logged out. Please log in again.", gr.update(visible=False), gr.update(visible=False), gr.update(visible=True)


# --- CORE FUNCTIONALITY (RESUME GENERATION - CORRECTED AND ENHANCED) ---

def generate_resume(name, skills, education, experience, prompt_extra):
    """Generates the AI text and the DOCX file with the structure of divya_resume.pdf."""
    
    if not name or not skills or not education:
        return "❌ Error: Please fill in Full Name, Key Skills, and Education to generate a resume.", "💡 No guidance available. Fill in required fields.", None
    
    safe_name = re.sub(r'[^a-zA-Z0-9_]', '', name.replace(' ', '_'))
    file_path = f"Professional_Resume_{safe_name}_{int(time.time())}.docx"

    # The prompt is used to get the AI-generated text output
    prompt = f"""Generate a clean, professional resume text for:
Name: {name}
Skills: {skills}
Education: {education}
Experience: {experience}
{prompt_extra if prompt_extra else ""}
Ensure the structure includes Summary, Skills, Education, Experience, and Certifications.
"""

    try:
        # --- Model generation logic (Robust for mock/real) ---
        if isinstance(model, MockModel):
            outputs = model.generate(prompt, max_new_tokens=400, num_return_sequences=1)
            raw_text = tokenizer.decode(outputs, skip_special_tokens=True) 
        else:
            inputs = tokenizer(prompt, return_tensors="pt")["input_ids"]
            outputs = model.generate(inputs, max_length=600, num_return_sequences=1)
            raw_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

        resume_text = raw_text.replace(prompt, "").strip()
        resume_text = re.sub(r"<.*?>", "", resume_text).strip()
        
        # Fallback to pure mock if the output is empty
        if not resume_text:
            resume_text = generate_llm_output(prompt)
                
        
        # --- Create Word document with EXTENDED STRUCTURE ---
        doc = Document()
        
        # 1. HEADER (NAME AND CONTACT INFO)
        name_p = doc.add_paragraph(name.upper())
        name_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        contact_p = doc.add_paragraph(
            f"Email id: [Your Email] | Contact no: [Your Phone] | LinkedIn: [Your LinkedIn URL]"
        )
        contact_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # 2. CAREER OBJECTIVE
        doc.add_heading("CAREER OBJECTIVE", level=1)
        doc.add_paragraph(
            f"To leverage my skills in programming, data analysis, and problem-solving to contribute to innovative projects and achieve professional growth in a dynamic environment, utilizing my knowledge of {skills}."
        )
        
        # 3. EDUCATION
        doc.add_heading("EDUCATION", level=1)
        doc.add_paragraph(education)
        
        # 4. SKILLS
        doc.add_heading("SKILLS", level=1)
        doc.add_paragraph(
            f"Programming Languages: {skills} \n"
            f"Frontend Technologies: HTML5, CSS3, JavaScript \n"
            f"Database: SQL \n"
            f"Soft Skills: Teamwork, Problem-solving, Communication"
        )
        
        # 5. INTERNSHIPS (Using the 'Experience' input field content)
        doc.add_heading("INTERNSHIPS", level=1)
        if experience.lower().strip() not in ["none", ""]:
            doc.add_paragraph(
                f"**Experience/Internship Details:**\n{experience}"
            )
        else:
            doc.add_paragraph("No formal internships or major experience listed. Eager to gain industry exposure.")
            
        # 6. PROJECTS (Adding a placeholder structure)
        doc.add_heading("PROJECTS", level=1)
        doc.add_paragraph(
            "• **Loan Approval Analytics:** Developed a classification model (If applicable, link to your experience/skills).\n"
            "• **Smart SDLC AI-Enhanced:** Built an AI-powered tool for the Software Development Life Cycle.\n"
            "• [Add another key project here]."
        )
        
        # 7. CERTIFICATIONS (Adding a placeholder structure)
        doc.add_heading("CERTIFICATIONS", level=1)
        doc.add_paragraph(
            "• Python Basics for Data Science - IBM (If applicable)\n"
            "• NPTEL certification in Social Networks (If applicable)\n"
            "• Generative AI with IBM Cloud - Smartinternz (If applicable)"
        )

        doc.save(file_path)

        guidance = f"""
### 💡 Resume Enhancement Tips:
- **Tailor:** Did you mention skills specific to the job you are applying for?
- **Metrics:** Use numbers to quantify your achievements (e.g., *Reduced costs by 15%*).
- **File:** Your DOCX file, **{file_path}**, is ready for download. The structure now includes **Objective, Internships, Projects, and Certifications** as requested.
"""
        
        return resume_text, guidance, file_path
    
    except Exception as e:
        error_msg = f"❌ Resume Generation Failed: An unexpected error occurred.\nError: {type(e).__name__}: {str(e)}"
        print(error_msg)
        return error_msg, f"💡 An error occurred during processing. Please check your inputs. The generated file was not saved to: {file_path}", None


# --- HR JOB POSTING FUNCTIONS (UNCHANGED) ---

def post_job(title, company, description):
    if not title or not company or not description:
        return gr.update(value=title), gr.update(value=company), gr.update(value=description), view_jobs_markdown(), f"❌ Error: All job fields are required to post."

    job_id = f"JID-{int(time.time())}"
    JOB_POSTINGS[job_id] = {
        "title": title,
        "company": company,
        "description": description,
        "posted_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    return gr.update(value=""), gr.update(value=""), gr.update(value=""), view_jobs_markdown(), f"✅ Success! Job '{title}' posted with ID: {job_id}"

def view_jobs_markdown():
    if not JOB_POSTINGS:
        return "No job postings available at this time."
        
    job_list_markdown = "### Available Job Openings\n"
    for jid, job in JOB_POSTINGS.items():
        job_list_markdown += f"#### {job['title']} at {job['company']}\n"
        job_list_markdown += f"**ID:** `{jid}` | **Posted:** {job['posted_at']}\n"
        truncated_desc = job['description'][:150] + ("..." if len(job['description']) > 150 else "")
        job_list_markdown += f"{truncated_desc}\n\n"
    return job_list_markdown

# --- GRADIO INTERFACE SETUP (UNCHANGED) ---

custom_css = """
.gradio-container { background: #f0f0f0; }
.textbox-bordered { border: 3px solid #1E3A8A; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.2); }
.custom-run-button { background-color: #0072CE !important; color: white !important; font-weight: bold; border-radius: 8px; padding: 10px 20px; }
.hr-header { color: #D61B1F; font-size: 1.5em; font-weight: bold; }
.applicant-header { color: #0072CE; font-size: 1.5em; font-weight: bold; }
.auth-title { color: #1E3A8A; font-size: 2em; }
"""

with gr.Blocks(css=custom_css) as demo:
    
    # --- State Variables ---
    auth_state = gr.State((None, "guest"))
    
    gr.Markdown("# 🏢 IBM Granite AI Career Portal")

    # 1. Define all Components
    with gr.Tabs() as main_tabs:
        
        # --- TAB 1: LOGIN / REGISTER ---
        with gr.TabItem("Authentication", elem_id="auth_tab") as auth_tab:
            gr.Markdown("<div class='auth-title'>Access Portal</div>")
            login_status_msg = gr.Markdown("Please login or register to use the portals.")
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 📝 New User Registration")
                    reg_user = gr.Textbox(label="Username")
                    reg_pass = gr.Textbox(label="Password", type="password")
                    reg_role = gr.Radio(["student", "hr"], label="Account Type")
                    register_btn = gr.Button("Register Account", variant="secondary")
                    reg_message = gr.Markdown("")
                    
                with gr.Column(scale=1):
                    gr.Markdown("### 🔑 Existing User Login")
                    login_user = gr.Textbox(label="Username")
                    login_pass = gr.Textbox(label="Password", type="password")
                    login_btn = gr.Button("Login to Portal", variant="primary")

        # --- TAB 2: APPLICANT PORTAL (Initially Hidden) ---
        with gr.TabItem("Applicant Portal", visible=False) as applicant_tab:
            
            gr.Markdown("<div class='applicant-header'>AI Resume Generation & Job Listings</div>")
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### Input Your Details")
                    # Use provided user data as defaults for convenience
                    name = gr.Textbox(label="Full Name", value="TADDETTI DIVYA")
                    skills = gr.Textbox(label="Key Skills (comma-separated)", placeholder="e.g., Python, SQL, Project Management", value="PYTHON, C, JS, JAVA")
                    education = gr.Textbox(label="Education", lines=2, placeholder="e.g., M.S. Computer Science, University X", value="BTECH (9.20)")
                    experience = gr.Textbox(label="Experience", lines=3, placeholder="Briefly describe your roles/projects/internships.", value="Cyber security AIMER Society (July-2024); Generative Al with IBM Cloud (July -2025)")
                    prompt_extra = gr.Textbox(label="Additional Instructions for AI", lines=2, placeholder="e.g., Focus on leadership skills for a managerial role.", value="NONE") 
                    run = gr.Button("✨ Generate Professional Resume", elem_classes=["custom-run-button"])
                
                with gr.Column(scale=2):
                    gr.Markdown("### Resume Output")
                    with gr.Tab("AI Generated Text"):
                        resume_out = gr.Textbox(label="📄 Review AI Generated Text (LLM Raw Output)", lines=15, elem_classes=["textbox-bordered"])
                    with gr.Tab("Guidance"):
                        guidance_out = gr.Markdown("💡 Guidance and Tips will appear here after generation.")
                    
                    download = gr.File(label="⬇️ Download Formatted .docx File")

            gr.Markdown("---")
            gr.Markdown("### 📜 Available Job Listings")
            job_context = gr.Markdown(view_jobs_markdown()) 
            
            logout_btn_applicant = gr.Button("Logout", variant="secondary")

        # --- TAB 3: HR PORTAL (Initially Hidden) ---
        with gr.TabItem("HR Portal", visible=False) as hr_tab:
            
            gr.Markdown("<div class='hr-header'>HR Management Portal: Post New Job Applications</div>")
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 📋 Post New Job")
                    job_title = gr.Textbox(label="Job Title", placeholder="e.g., Senior Data Scientist")
                    job_company = gr.Textbox(label="Company Name", placeholder="e.g., IBM")
                    job_description = gr.Textbox(label="Job Description", lines=5, placeholder="Paste the full job description here.")
                    post_btn = gr.Button("Post Job", variant="primary")
                    posting_message = gr.Markdown("Job posting status will appear here.")
                    
                with gr.Column(scale=2):
                    gr.Markdown("### 📜 Current Active Job Postings")
                    current_jobs_out = gr.Markdown(view_jobs_markdown(), visible=True)

            logout_btn_hr = gr.Button("Logout", variant="secondary")
            
    
    # 2. Define all Event Handlers (Click functions) AFTER all components are defined

    # --- Registration Logic ---
    register_btn.click(
        register_user,
        inputs=[reg_user, reg_pass, reg_role],
        outputs=[
            reg_message, 
            reg_user, 
            reg_pass, 
            reg_role,
            login_user, 
            login_pass 
        ]
    )
    
    # --- Login Logic ---
    login_btn.click(
        user_login,
        inputs=[login_user, login_pass],
        outputs=[
            auth_state, 
            login_status_msg, 
            applicant_tab, 
            hr_tab, 
            auth_tab 
        ]
    )

    # --- Applicant Resume Generation Logic ---
    run.click(
        generate_resume,
        inputs=[name, skills, education, experience, prompt_extra],
        outputs=[resume_out, guidance_out, download] 
    )
    
    # --- HR Post Job Logic ---
    post_btn.click(
        post_job,
        inputs=[job_title, job_company, job_description],
        outputs=[job_title, job_company, job_description, current_jobs_out, posting_message]
    ).then(
        view_jobs_markdown, 
        inputs=[],
        outputs=[job_context] 
    )
    
    # --- LOGOUT Logic (Shared) ---
    logout_btn_applicant.click(
        user_logout,
        inputs=[],
        outputs=[auth_state, login_status_msg, applicant_tab, hr_tab, auth_tab]
    )
    
    logout_btn_hr.click(
        user_logout,
        inputs=[],
        outputs=[auth_state, login_status_msg, applicant_tab, hr_tab, auth_tab]
    )

demo.launch()'''

# pip install gradio transformers python-docx
'''
import gradio as gr
from transformers import AutoTokenizer, AutoModelForCausalLM
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import re
import os
import time

# --- MOCK DATABASE AND STATE ---
USER_DB = {
    "test_hr": {"password": "hr_password", "role": "hr"},
    "test_student": {"password": "student_password", "role": "student"}
}
JOB_POSTINGS = {} 

# --- MOCK IMPLEMENTATION DEFINITION ---
def generate_llm_output(prompt):
    """Generates a structured mock AI response."""
    name_match = re.search(r"Name: (.*)", prompt)
    skills_match = re.search(r"Skills: (.*)", prompt)
    name = name_match.group(1).strip() if name_match else "Applicant Name"
    skills = skills_match.group(1).strip() if skills_match else "Python, Leadership, SQL"
    
    return f"***DUMMY AI RESPONSE***\n\n**SUMMARY:** Highly motivated individual ({name}) with a strong foundation in {skills}. Proven ability to tackle complex challenges and drive results.\n\n**SKILLS:** {skills}\n\n**EXPERIENCE:** Simulated job experience here, demonstrating proficiency in key skills.\n\n**EDUCATION:** University details here."

class MockModel:
    def generate(self, input_ids, max_new_tokens, num_return_sequences):
        # In mock mode, we just return the input text (prompt) for the tokenizer to decode
        return {"input_ids": input_ids} 

class MockTokenizer:
    def __init__(self): self.eos_token = ""
    def __call__(self, text, *args, **kwargs): return {"input_ids": text}
    def decode(self, tokens, skip_special_tokens=True): 
        if isinstance(tokens, dict) and "input_ids" in tokens:
            tokens = tokens["input_ids"]
        if isinstance(tokens, str):
            return generate_llm_output(tokens)
        return generate_llm_output("Default Name: Default, Skills: Default")


# --- IBM Granite Model Loading (FIXED: MOCK FALLBACK ENSURED) ---

tokenizer = None
model = None

try:
    # Attempt to load the real model (will likely fail, triggering the mock)
    tokenizer = AutoTokenizer.from_pretrained("ibm-granite/granite-3.3-2b-instruct")
    model = AutoModelForCausalLM.from_pretrained("ibm-granite/granite-3.3-2b-instruct")
    print("SUCCESS: Loaded IBM Granite model.")
except Exception as e:
    print(f"Warning: Could not load Granite model. Using DUMMY/MOCK function. Error: {e}")
    # CRITICAL FIX: Assign mock objects to global variables
    model = MockModel()
    tokenizer = MockTokenizer()


# --- AUTHENTICATION FUNCTIONS (UNCHANGED) ---

def register_user(username, password, role):
    if not username or not password or not role:
        return "❌ Registration failed: All fields are required.", gr.update(value=""), gr.update(value=""), gr.update(value=None), gr.update(value=""), gr.update(value="")
               
    username = username.strip()
    password = password.strip()
    
    if username in USER_DB:
        return f"❌ Registration failed: User '{username}' already exists.", gr.update(value=""), gr.update(value=""), gr.update(value=None), gr.update(value=""), gr.update(value="")
    
    USER_DB[username] = {"password": password, "role": role}
    
    return f"✅ Success! User '{username}' registered as **{role.upper()}**. Please proceed to the Login section.", gr.update(value=""), gr.update(value=""), gr.update(value=None), gr.update(value=""), gr.update(value="")


def user_login(username, password):
    username = username.strip()
    password = password.strip()
    
    if username in USER_DB:
        if USER_DB[username]["password"] == password:
            role = USER_DB[username]["role"]
            
            if role == "student":
                return (username, role), f"✅ Login Success! Welcome, {username} ({role.upper()}).", gr.update(visible=True), gr.update(visible=False), gr.update(visible=False)
            elif role == "hr":
                return (username, role), f"✅ Login Success! Welcome, {username} ({role.upper()}).", gr.update(visible=False), gr.update(visible=True), gr.update(visible=False)
        else:
            return (None, "guest"), "❌ Login Failed: Invalid password.", gr.update(visible=False), gr.update(visible=False), gr.update(visible=True)
    else:
        return (None, "guest"), "❌ Login Failed: Invalid username or password.", gr.update(visible=False), gr.update(visible=False), gr.update(visible=True)

def user_logout():
    return (None, "guest"), "👋 Logged out. Please log in again.", gr.update(visible=False), gr.update(visible=False), gr.update(visible=True)


# --- CORE FUNCTIONALITY (RESUME GENERATION - CORRECTED AND ENHANCED) ---

def generate_resume(name, skills, education, experience, prompt_extra):
    """Generates the AI text and the DOCX file with the structure of divya_resume.pdf."""
    
    if not name or not skills or not education:
        return "❌ Error: Please fill in Full Name, Key Skills, and Education to generate a resume.", "💡 No guidance available. Fill in required fields.", None
    
    safe_name = re.sub(r'[^a-zA-Z0-9_]', '', name.replace(' ', '_'))
    file_path = f"Professional_Resume_{safe_name}_{int(time.time())}.docx"

    # The prompt is used to get the AI-generated text output
    prompt = f"""Generate a clean, professional resume text for:
Name: {name}
Skills: {skills}
Education: {education}
Experience: {experience}
{prompt_extra if prompt_extra else ""}
Ensure the structure includes Summary, Skills, Education, Experience, and Certifications.
"""

    try:
        # --- Model generation logic (Robust for mock/real) ---
        if isinstance(model, MockModel):
            outputs = model.generate(prompt, max_new_tokens=400, num_return_sequences=1)
            raw_text = tokenizer.decode(outputs, skip_special_tokens=True) 
        else:
            inputs = tokenizer(prompt, return_tensors="pt")["input_ids"]
            outputs = model.generate(inputs, max_length=600, num_return_sequences=1)
            raw_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

        resume_text = raw_text.replace(prompt, "").strip()
        resume_text = re.sub(r"<.*?>", "", resume_text).strip()
        
        # Fallback to pure mock if the output is empty
        if not resume_text:
            resume_text = generate_llm_output(prompt)
                
        
        # --- Create Word document with EXTENDED STRUCTURE to match the PDF ---
        doc = Document()
        
        # 1. HEADER (NAME AND CONTACT INFO)
        name_p = doc.add_paragraph(name.upper())
        name_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        contact_p = doc.add_paragraph(
            f"Email id: [Your Email] | Contact no: [Your Phone] | LinkedIn: [Your LinkedIn URL]"
        )
        contact_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # 2. CAREER OBJECTIVE
        doc.add_heading("CAREER OBJECTIVE", level=1)
        doc.add_paragraph(
            f"To leverage my skills in programming, data analysis, and problem-solving to contribute to innovative projects and achieve professional growth in a dynamic environment, utilizing my knowledge of {skills}."
        )
        
        # 3. EDUCATION
        doc.add_heading("EDUCATION", level=1)
        doc.add_paragraph(education)
        
        # 4. SKILLS (Manually structured as per the PDF blueprint)
        doc.add_heading("SKILLS", level=1)
        doc.add_paragraph(
            f"Programming Languages: {skills} \n"
            f"Frontend Technologies: HTML5, CSS3, JavaScript \n"
            f"Database: SQL \n"
            f"Soft Skills: Teamwork, Problem-solving, Communication"
        )
        
        # 5. INTERNSHIPS (Using the 'Experience' input field content)
        doc.add_heading("INTERNSHIPS", level=1)
        if experience.lower().strip() not in ["none", ""]:
            # Use the experience field to detail internships/roles
            doc.add_paragraph(experience) 
        else:
            doc.add_paragraph("No formal internships or major experience listed. Eager to gain industry exposure.")
            
        # 6. PROJECTS (Placeholder structure based on PDF)
        doc.add_heading("PROJECTS", level=1)
        doc.add_paragraph(
            "• **Loan Approval Analytics:** Developed a classification model.\n"
            "• **Smart SDLC AI-Enhanced:** Built an AI-powered tool for the Software Development Life Cycle.\n"
            "• [Add another key project here]."
        )
        
        # 7. CERTIFICATIONS (Placeholder structure based on PDF)
        doc.add_heading("CERTIFICATIONS", level=1)
        doc.add_paragraph(
            "• Python Basics for Data Science - IBM\n"
            "• NPTEL certification in Social Networks\n"
            "• Generative AI with IBM Cloud - Smartinternz"
        )

        doc.save(file_path)

        guidance = f"""
### 💡 Resume Enhancement Tips:
- **Tailor:** Did you mention skills specific to the job you are applying for?
- **Metrics:** Use numbers to quantify your achievements (e.g., *Reduced costs by 15%*).
- **File:** Your DOCX file, **{file_path}**, is ready for download. The structure now includes **Objective, Internships, Projects, and Certifications** as requested.
"""
        
        return resume_text, guidance, file_path
    
    except Exception as e:
        error_msg = f"❌ Resume Generation Failed: An unexpected error occurred.\nError: {type(e).__name__}: {str(e)}"
        print(error_msg)
        return error_msg, f"💡 An error occurred during processing. Please check your inputs. The generated file was not saved to: {file_path}", None


# --- HR JOB POSTING FUNCTIONS (UNCHANGED) ---

def post_job(title, company, description):
    if not title or not company or not description:
        return gr.update(value=title), gr.update(value=company), gr.update(value=description), view_jobs_markdown(), f"❌ Error: All job fields are required to post."

    job_id = f"JID-{int(time.time())}"
    JOB_POSTINGS[job_id] = {
        "title": title,
        "company": company,
        "description": description,
        "posted_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    return gr.update(value=""), gr.update(value=""), gr.update(value=""), view_jobs_markdown(), f"✅ Success! Job '{title}' posted with ID: {job_id}"

def view_jobs_markdown():
    if not JOB_POSTINGS:
        return "No job postings available at this time."
        
    job_list_markdown = "### Available Job Openings\n"
    for jid, job in JOB_POSTINGS.items():
        job_list_markdown += f"#### {job['title']} at {job['company']}\n"
        job_list_markdown += f"**ID:** `{jid}` | **Posted:** {job['posted_at']}\n"
        truncated_desc = job['description'][:150] + ("..." if len(job['description']) > 150 else "")
        job_list_markdown += f"{truncated_desc}\n\n"
    return job_list_markdown

# --- GRADIO INTERFACE SETUP (UNCHANGED) ---

custom_css = """
.gradio-container { background: #f0f0f0; }
.textbox-bordered { border: 3px solid #1E3A8A; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.2); }
.custom-run-button { background-color: #0072CE !important; color: white !important; font-weight: bold; border-radius: 8px; padding: 10px 20px; }
.hr-header { color: #D61B1F; font-size: 1.5em; font-weight: bold; }
.applicant-header { color: #0072CE; font-size: 1.5em; font-weight: bold; }
.auth-title { color: #1E3A8A; font-size: 2em; }
"""

with gr.Blocks(css=custom_css) as demo:
    
    # --- State Variables ---
    auth_state = gr.State((None, "guest"))
    
    gr.Markdown("# 🏢 IBM Granite AI Career Portal")

    # 1. Define all Components
    with gr.Tabs() as main_tabs:
        
        # --- TAB 1: LOGIN / REGISTER ---
        with gr.TabItem("Authentication", elem_id="auth_tab") as auth_tab:
            gr.Markdown("<div class='auth-title'>Access Portal</div>")
            login_status_msg = gr.Markdown("Please login or register to use the portals.")
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 📝 New User Registration")
                    reg_user = gr.Textbox(label="Username")
                    reg_pass = gr.Textbox(label="Password", type="password")
                    reg_role = gr.Radio(["student", "hr"], label="Account Type")
                    register_btn = gr.Button("Register Account", variant="secondary")
                    reg_message = gr.Markdown("")
                    
                with gr.Column(scale=1):
                    gr.Markdown("### 🔑 Existing User Login")
                    login_user = gr.Textbox(label="Username")
                    login_pass = gr.Textbox(label="Password", type="password")
                    login_btn = gr.Button("Login to Portal", variant="primary")

        # --- TAB 2: APPLICANT PORTAL (Initially Hidden) ---
        with gr.TabItem("Applicant Portal", visible=False) as applicant_tab:
            
            gr.Markdown("<div class='applicant-header'>AI Resume Generation & Job Listings</div>")
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### Input Your Details")
                    # Use provided user data as defaults for convenience
                    name = gr.Textbox(label="Full Name")
                    skills = gr.Textbox(label="Key Skills (comma-separated)", placeholder="e.g., Python, SQL, Project Management")
                    education = gr.Textbox(label="Education", lines=2, placeholder="e.g., M.S. Computer Science, University X")
                    experience = gr.Textbox(label="Experience", lines=3, placeholder="Briefly describe your roles/projects/internships.")
                    prompt_extra = gr.Textbox(label="Additional Instructions for AI", lines=2, placeholder="e.g., Focus on leadership skills for a managerial role.") 
                    run = gr.Button("✨ Generate Professional Resume", elem_classes=["custom-run-button"])
                
                with gr.Column(scale=2):
                    gr.Markdown("### Resume Output")
                    with gr.Tab("AI Generated Text"):
                        resume_out = gr.Textbox(label="📄 Review AI Generated Text (LLM Raw Output)", lines=15, elem_classes=["textbox-bordered"])
                    with gr.Tab("Guidance"):
                        guidance_out = gr.Markdown("💡 Guidance and Tips will appear here after generation.")
                    
                    download = gr.File(label="⬇️ Download Formatted .docx File")

            gr.Markdown("---")
            gr.Markdown("### 📜 Available Job Listings")
            job_context = gr.Markdown(view_jobs_markdown()) 
            
            logout_btn_applicant = gr.Button("Logout", variant="secondary")

        # --- TAB 3: HR PORTAL (Initially Hidden) ---
        with gr.TabItem("HR Portal", visible=False) as hr_tab:
            
            gr.Markdown("<div class='hr-header'>HR Management Portal: Post New Job Applications</div>")
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 📋 Post New Job")
                    job_title = gr.Textbox(label="Job Title", placeholder="e.g., Senior Data Scientist")
                    job_company = gr.Textbox(label="Company Name", placeholder="e.g., IBM")
                    job_description = gr.Textbox(label="Job Description", lines=5, placeholder="Paste the full job description here.")
                    post_btn = gr.Button("Post Job", variant="primary")
                    posting_message = gr.Markdown("Job posting status will appear here.")
                    
                with gr.Column(scale=2):
                    gr.Markdown("### 📜 Current Active Job Postings")
                    current_jobs_out = gr.Markdown(view_jobs_markdown(), visible=True)

            logout_btn_hr = gr.Button("Logout", variant="secondary")
            
    
    # 2. Define all Event Handlers (Click functions) AFTER all components are defined

    # --- Registration Logic ---
    register_btn.click(
        register_user,
        inputs=[reg_user, reg_pass, reg_role],
        outputs=[
            reg_message, 
            reg_user, 
            reg_pass, 
            reg_role,
            login_user, 
            login_pass 
        ]
    )
    
    # --- Login Logic ---
    login_btn.click(
        user_login,
        inputs=[login_user, login_pass],
        outputs=[
            auth_state, 
            login_status_msg, 
            applicant_tab, 
            hr_tab, 
            auth_tab 
        ]
    )

    # --- Applicant Resume Generation Logic ---
    run.click(
        generate_resume,
        inputs=[name, skills, education, experience, prompt_extra],
        outputs=[resume_out, guidance_out, download] 
    )
    
    # --- HR Post Job Logic ---
    post_btn.click(
        post_job,
        inputs=[job_title, job_company, job_description],
        outputs=[job_title, job_company, job_description, current_jobs_out, posting_message]
    ).then(
        view_jobs_markdown, 
        inputs=[],
        outputs=[job_context] 
    )
    
    # --- LOGOUT Logic (Shared) ---
    logout_btn_applicant.click(
        user_logout,
        inputs=[],
        outputs=[auth_state, login_status_msg, applicant_tab, hr_tab, auth_tab]
    )
    
    logout_btn_hr.click(
        user_logout,
        inputs=[],
        outputs=[auth_state, login_status_msg, applicant_tab, hr_tab, auth_tab]
    )

demo.launch()'''

# pip install gradio transformers python-docx
'''
import gradio as gr
from transformers import AutoTokenizer, AutoModelForCausalLM
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import re
import os
import time

# --- MOCK DATABASE AND STATE ---
USER_DB = {
    "test_hr": {"password": "hr_password", "role": "hr"},
    "test_student": {"password": "student_password", "role": "student"}
}
JOB_POSTINGS = {} 

# --- MOCK IMPLEMENTATION DEFINITION ---
def generate_llm_output(prompt):
    """Generates a structured mock AI response."""
    name_match = re.search(r"Name: (.*)", prompt)
    skills_match = re.search(r"Skills: (.*)", prompt)
    name = name_match.group(1).strip() if name_match else "Applicant Name"
    skills = skills_match.group(1).strip() if skills_match else "Python, Leadership, SQL"
    
    return f"***DUMMY AI RESPONSE***\n\n**SUMMARY:** Highly motivated individual ({name}) with a strong foundation in {skills}. Proven ability to tackle complex challenges and drive results.\n\n**SKILLS:** {skills}\n\n**EXPERIENCE:** Simulated job experience here, demonstrating proficiency in key skills.\n\n**EDUCATION:** University details here."

class MockModel:
    def generate(self, input_ids, max_new_tokens, num_return_sequences):
        return {"input_ids": input_ids} 

class MockTokenizer:
    def __init__(self): self.eos_token = ""
    def __call__(self, text, *args, **kwargs): return {"input_ids": text}
    def decode(self, tokens, skip_special_tokens=True): 
        if isinstance(tokens, dict) and "input_ids" in tokens:
            tokens = tokens["input_ids"]
        if isinstance(tokens, str):
            return generate_llm_output(tokens)
        return generate_llm_output("Default Name: Default, Skills: Default")


# --- IBM Granite Model Loading (MOCK FALLBACK) ---

tokenizer = None
model = None

try:
    tokenizer = AutoTokenizer.from_pretrained("ibm-granite/granite-3.3-2b-instruct")
    model = AutoModelForCausalLM.from_pretrained("ibm-granite/granite-3.3-2b-instruct")
    print("SUCCESS: Loaded IBM Granite model.")
except Exception as e:
    print(f"Warning: Could not load Granite model. Using DUMMY/MOCK function. Error: {e}")
    model = MockModel()
    tokenizer = MockTokenizer()


# --- AUTHENTICATION FUNCTIONS (UNCHANGED) ---

def register_user(username, password, role):
    if not username or not password or not role:
        return "❌ Registration failed: All fields are required.", gr.update(value=""), gr.update(value=""), gr.update(value=None), gr.update(value=""), gr.update(value="")
               
    username = username.strip()
    password = password.strip()
    
    if username in USER_DB:
        return f"❌ Registration failed: User '{username}' already exists.", gr.update(value=""), gr.update(value=""), gr.update(value=None), gr.update(value=""), gr.update(value="")
    
    USER_DB[username] = {"password": password, "role": role}
    
    return f"✅ Success! User '{username}' registered as **{role.upper()}**. Please proceed to the Login section.", gr.update(value=""), gr.update(value=""), gr.update(value=None), gr.update(value=""), gr.update(value="")


def user_login(username, password):
    username = username.strip()
    password = password.strip()
    
    if username in USER_DB:
        if USER_DB[username]["password"] == password:
            role = USER_DB[username]["role"]
            
            if role == "student":
                return (username, role), f"✅ Login Success! Welcome, {username} ({role.upper()}).", gr.update(visible=True), gr.update(visible=False), gr.update(visible=False)
            elif role == "hr":
                return (username, role), f"✅ Login Success! Welcome, {username} ({role.upper()}).", gr.update(visible=False), gr.update(visible=True), gr.update(visible=False)
        else:
            return (None, "guest"), "❌ Login Failed: Invalid password.", gr.update(visible=False), gr.update(visible=False), gr.update(visible=True)
    else:
        return (None, "guest"), "❌ Login Failed: Invalid username or password.", gr.update(visible=False), gr.update(visible=False), gr.update(visible=True)

def user_logout():
    return (None, "guest"), "👋 Logged out. Please log in again.", gr.update(visible=False), gr.update(visible=False), gr.update(visible=True)


# --- CORE FUNCTIONALITY (RESUME GENERATION - FULLY UPDATED) ---

def generate_resume(name, email_id, contact_no, linkedin_url, objective, skills, education, experience, projects_input, certifications_input, prompt_extra):
    """Generates the AI text and the DOCX file with all fields from divya_resume.pdf."""
    
    if not name or not skills or not education:
        return "❌ Error: Please fill in Full Name, Key Skills, and Education to generate a resume.", "💡 No guidance available. Fill in required fields.", None
    
    safe_name = re.sub(r'[^a-zA-Z0-9_]', '', name.replace(' ', '_'))
    file_path = f"Professional_Resume_{safe_name}_{int(time.time())}.docx"

    # The prompt is used to get the AI-generated text output
    prompt = f"""Generate a clean, professional resume text for:
Name: {name}
Skills: {skills}
Education: {education}
Experience: {experience}
{prompt_extra if prompt_extra else ""}
Ensure the structure includes Summary, Skills, Education, Experience, and Certifications.
"""

    try:
        # --- Model generation logic (Robust for mock/real) ---
        if isinstance(model, MockModel):
            outputs = model.generate(prompt, max_new_tokens=400, num_return_sequences=1)
            raw_text = tokenizer.decode(outputs, skip_special_tokens=True) 
        else:
            inputs = tokenizer(prompt, return_tensors="pt")["input_ids"]
            outputs = model.generate(inputs, max_length=600, num_return_sequences=1)
            raw_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

        resume_text = raw_text.replace(prompt, "").strip()
        resume_text = re.sub(r"<.*?>", "", resume_text).strip()
        if not resume_text:
            resume_text = generate_llm_output(prompt)
                
        
        # --- Create Word document with EXTENDED STRUCTURE to match the PDF ---
        doc = Document()
        
        # 1. HEADER (NAME and Contact Details)
        name_p = doc.add_paragraph(name.upper())
        name_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Use the provided contact fields directly
        contact_p = doc.add_paragraph(
            f"Email id: {email_id} | Contact no: {contact_no} | LinkedIn: {linkedin_url}"
        )
        contact_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # 2. CAREER OBJECTIVE
        doc.add_heading("CAREER OBJECTIVE", level=1)
        objective_text = objective if objective.strip() else "To leverage my skills in programming, data analysis, and problem-solving to contribute to innovative projects and achieve professional growth in a dynamic environment."
        doc.add_paragraph(objective_text)
        
        # 3. EDUCATION
        doc.add_heading("EDUCATION", level=1)
        doc.add_paragraph(education)
        
        # 4. SKILLS (Manually structured, using user's input for Programming Languages)
        doc.add_heading("SKILLS", level=1)
        doc.add_paragraph(
            f"Programming Languages: {skills} \n"
            f"Frontend Technologies: HTML5, CSS3, Bootstrap \n"
            f"Database: SQL \n"
            f"Soft Skills: Teamwork, Problem-solving." # Using the explicit soft skills from the PDF
        )
        
        # 5. INTERNSHIPS (Using the 'Experience' input field content)
        doc.add_heading("INTERNSHIPS", level=1)
        if experience.lower().strip() not in ["none", ""]:
            # Use the experience field, which corresponds to INTERNSHIPS in the PDF
            doc.add_paragraph(experience) 
        else:
            doc.add_paragraph("No formal internships or major experience listed.")
            
        # 6. PROJECTS 
        doc.add_heading("PROJECTS", level=1)
        if projects_input.lower().strip() not in ["none", ""]:
            # Use the user's project input directly
            doc.add_paragraph(projects_input)
        else:
            doc.add_paragraph("• Loan Approval Analytics: A Classification-Based Data Mining Approach\n• Smart SDLC AI-Enhanced Software Development Life Cycle")
        
        # 7. CERTIFICATIONS 
        doc.add_heading("CERTIFICATIONS", level=1)
        if certifications_input.lower().strip() not in ["none", ""]:
            # Use the user's certifications input directly
            doc.add_paragraph(certifications_input)
        else:
            doc.add_paragraph("• Python Basics for Data Science - IBM\n• NPTEL certification in Social Networks\n• Generative AI with IBM Cloud - Smartinternz")

        doc.save(file_path)

        guidance = f"""
### 💡 Resume Enhancement Tips:
- **Tailor:** Did you mention skills specific to the job you are applying for?
- **Metrics:** Use numbers to quantify your achievements (e.g., *Reduced costs by 15%*).
- **File:** Your DOCX file, **{file_path}**, is ready for download.
"""
        
        return resume_text, guidance, file_path
    
    except Exception as e:
        error_msg = f"❌ Resume Generation Failed: An unexpected error occurred.\nError: {type(e).__name__}: {str(e)}"
        print(error_msg)
        return error_msg, f"💡 An error occurred during processing. Please check your inputs. The generated file was not saved to: {file_path}", None


# --- HR JOB POSTING FUNCTIONS (UNCHANGED) ---

def post_job(title, company, description):
    if not title or not company or not description:
        return gr.update(value=title), gr.update(value=company), gr.update(value=description), view_jobs_markdown(), f"❌ Error: All job fields are required to post."

    job_id = f"JID-{int(time.time())}"
    JOB_POSTINGS[job_id] = {
        "title": title,
        "company": company,
        "description": description,
        "posted_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    return gr.update(value=""), gr.update(value=""), gr.update(value=""), view_jobs_markdown(), f"✅ Success! Job '{title}' posted with ID: {job_id}"

def view_jobs_markdown():
    if not JOB_POSTINGS:
        return "No job postings available at this time."
        
    job_list_markdown = "### Available Job Openings\n"
    for jid, job in JOB_POSTINGS.items():
        job_list_markdown += f"#### {job['title']} at {job['company']}\n"
        job_list_markdown += f"**ID:** `{jid}` | **Posted:** {job['posted_at']}\n"
        truncated_desc = job['description'][:150] + ("..." if len(job['description']) > 150 else "")
        job_list_markdown += f"{truncated_desc}\n\n"
    return job_list_markdown

# --- GRADIO INTERFACE SETUP (UPDATED with all PDF fields) ---

custom_css = """
.gradio-container { background: #f0f0f0; }
.textbox-bordered { border: 3px solid #1E3A8A; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.2); }
.custom-run-button { background-color: #0072CE !important; color: white !important; font-weight: bold; border-radius: 8px; padding: 10px 20px; }
.hr-header { color: #D61B1F; font-size: 1.5em; font-weight: bold; }
.applicant-header { color: #0072CE; font-size: 1.5em; font-weight: bold; }
.auth-title { color: #1E3A8A; font-size: 2em; }
"""

with gr.Blocks(css=custom_css) as demo:
    
    # --- State Variables ---
    auth_state = gr.State((None, "guest"))
    
    gr.Markdown("# 🏢 IBM Granite AI Career Portal")

    with gr.Tabs() as main_tabs:
        
        # --- TAB 1: LOGIN / REGISTER (Unchanged) ---
        with gr.TabItem("Authentication", elem_id="auth_tab") as auth_tab:
            gr.Markdown("<div class='auth-title'>Access Portal</div>")
            login_status_msg = gr.Markdown("Please login or register to use the portals.")
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 📝 New User Registration")
                    reg_user = gr.Textbox(label="Username")
                    reg_pass = gr.Textbox(label="Password", type="password")
                    reg_role = gr.Radio(["student", "hr"], label="Account Type")
                    register_btn = gr.Button("Register Account", variant="secondary")
                    reg_message = gr.Markdown("")
                    
                with gr.Column(scale=1):
                    gr.Markdown("### 🔑 Existing User Login")
                    login_user = gr.Textbox(label="Username")
                    login_pass = gr.Textbox(label="Password", type="password")
                    login_btn = gr.Button("Login to Portal", variant="primary")

        # --- TAB 2: APPLICANT PORTAL (Updated with all fields) ---
        with gr.TabItem("Applicant Portal", visible=False) as applicant_tab:
            
            gr.Markdown("<div class='applicant-header'>AI Resume Generation & Job Listings</div>")
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 👤 Personal Details (From PDF Header)")
                    name = gr.Textbox(label="Full Name", value="Divya Tadisetti")
                    
                    with gr.Row():
                        email_id = gr.Textbox(label="Email id", value="dtadisetti8@gmail.com")
                        contact_no = gr.Textbox(label="Contact no", value="9989059362")
                    linkedin_url = gr.Textbox(label="LinkedIn URL", value="divya-tadisetti-161336304")
                    
                    gr.Markdown("---")
                    gr.Markdown("### 📚 Core Content")
                    objective = gr.Textbox(label="Career Objective", lines=3, placeholder="To leverage my skills...", value="To leverage my skills in programming, data analysis, and problem-solving to contribute to innovative projects and achieve professional growth in a dynamic environment.")
                    skills = gr.Textbox(label="Key Skills (Programming/Tech)", value="C, Python, Java, HTML5, CSS3, Bootstrap, SQL")
                    education = gr.Textbox(label="Education", lines=2, value="Seshadri Rao Gudlavalleru Engineering College, BTech in Computer Science and Engineering | GPA: 9.20 | 2026")
                    
                    gr.Markdown("---")
                    gr.Markdown("### 💼 Experience & Achievements")
                    experience = gr.Textbox(label="Internships / Experience", lines=3, placeholder="List your internships and professional roles here. (Maps to INTERNSHIPS)", value="Cyber security AIMER Society (July-2024): Learned threat detection and risk assessment; Generative Al with IBM Cloud- Smartinternz(July -2025): Built small-scale Al model deployment project")
                    projects_input = gr.Textbox(label="Projects", lines=3, placeholder="Separate projects with a new line or bullet points.", value="Loan Approval Analytics: A Classification-Based Data Mining Approach; Smart SDLC AI-Enhanced Software Development Life Cycle")
                    certifications_input = gr.Textbox(label="Certifications", lines=2, placeholder="List certifications separated by new lines.", value="Python Basics for Data Science - IBM; NPTEL certification in Social Networks")
                    
                    gr.Markdown("---")
                    prompt_extra = gr.Textbox(label="Additional Instructions for AI", lines=1, placeholder="e.g., Focus on leadership skills for a managerial role.", value="NONE") 
                    run = gr.Button("✨ Generate Professional Resume", elem_classes=["custom-run-button"])
                
                with gr.Column(scale=2):
                    gr.Markdown("### Resume Output")
                    with gr.Tab("AI Generated Text"):
                        resume_out = gr.Textbox(label="📄 Review AI Generated Text (LLM Raw Output)", lines=15, elem_classes=["textbox-bordered"])
                    with gr.Tab("Guidance"):
                        guidance_out = gr.Markdown("💡 Guidance and Tips will appear here after generation.")
                    
                    download = gr.File(label="⬇️ Download Formatted .docx File")

            gr.Markdown("---")
            gr.Markdown("### 📜 Available Job Listings")
            job_context = gr.Markdown(view_jobs_markdown()) 
            
            logout_btn_applicant = gr.Button("Logout", variant="secondary")

        # --- TAB 3: HR PORTAL (Unchanged) ---
        with gr.TabItem("HR Portal", visible=False) as hr_tab:
            
            gr.Markdown("<div class='hr-header'>HR Management Portal: Post New Job Applications</div>")
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 📋 Post New Job")
                    job_title = gr.Textbox(label="Job Title", placeholder="e.g., Senior Data Scientist")
                    job_company = gr.Textbox(label="Company Name", placeholder="e.g., IBM")
                    job_description = gr.Textbox(label="Job Description", lines=5, placeholder="Paste the full job description here.")
                    post_btn = gr.Button("Post Job", variant="primary")
                    posting_message = gr.Markdown("Job posting status will appear here.")
                    
                with gr.Column(scale=2):
                    gr.Markdown("### 📜 Current Active Job Postings")
                    current_jobs_out = gr.Markdown(view_jobs_markdown(), visible=True)

            logout_btn_hr = gr.Button("Logout", variant="secondary")
            
    
    # 2. Define all Event Handlers (Click functions)

    # --- Registration Logic (Unchanged) ---
    register_btn.click(
        register_user,
        inputs=[reg_user, reg_pass, reg_role],
        outputs=[reg_message, reg_user, reg_pass, reg_role, login_user, login_pass]
    )
    
    # --- Login Logic (Unchanged) ---
    login_btn.click(
        user_login,
        inputs=[login_user, login_pass],
        outputs=[auth_state, login_status_msg, applicant_tab, hr_tab, auth_tab]
    )

    # --- Applicant Resume Generation Logic (UPDATED to use all PDF fields) ---
    run.click(
        generate_resume,
        inputs=[
            name, 
            email_id, 
            contact_no, 
            linkedin_url, 
            objective, 
            skills, 
            education, 
            experience, 
            projects_input, 
            certifications_input, 
            prompt_extra
        ],
        outputs=[resume_out, guidance_out, download] 
    )
    
    # --- HR Post Job Logic (Unchanged) ---
    post_btn.click(
        post_job,
        inputs=[job_title, job_company, job_description],
        outputs=[job_title, job_company, job_description, current_jobs_out, posting_message]
    ).then(
        view_jobs_markdown, 
        inputs=[],
        outputs=[job_context] 
    )
    
    # --- LOGOUT Logic (Unchanged) ---
    logout_btn_applicant.click(
        user_logout,
        inputs=[],
        outputs=[auth_state, login_status_msg, applicant_tab, hr_tab, auth_tab]
    )
    
    logout_btn_hr.click(
        user_logout,
        inputs=[],
        outputs=[auth_state, login_status_msg, applicant_tab, hr_tab, auth_tab]
    )

demo.launch()'''

# pip install gradio transformers python-docx
'''
import gradio as gr
from transformers import AutoTokenizer, AutoModelForCausalLM
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import re
import os
import time
import random # Used for unique job ID generation

# --- MOCK DATABASE AND STATE ---
USER_DB = {
    "test_hr": {"password": "hr_password", "role": "hr"},
    "test_student": {"password": "student_password", "role": "student"}
}
JOB_POSTINGS = {} 

# --- MOCK IMPLEMENTATION DEFINITION ---
def generate_llm_output(prompt):
    """Generates a structured mock AI response."""
    name_match = re.search(r"Name: (.*)", prompt)
    skills_match = re.search(r"Skills: (.*)", prompt)
    name = name_match.group(1).strip() if name_match else "Applicant Name"
    skills = skills_match.group(1).strip() if skills_match else "Python, Leadership, SQL"
    
    return f"***DUMMY AI RESPONSE***\n\n**SUMMARY:** Highly motivated individual ({name}) with a strong foundation in {skills}. Proven ability to tackle complex challenges and drive results.\n\n**SKILLS:** {skills}\n\n**EXPERIENCE:** Simulated job experience here, demonstrating proficiency in key skills.\n\n**EDUCATION:** University details here."

class MockModel:
    def generate(self, input_ids, max_new_tokens, num_return_sequences):
        return {"input_ids": input_ids} 

class MockTokenizer:
    def __init__(self): self.eos_token = ""
    def __call__(self, text, *args, **kwargs): return {"input_ids": text}
    def decode(self, tokens, skip_special_tokens=True): 
        if isinstance(tokens, dict) and "input_ids" in tokens:
            tokens = tokens["input_ids"]
        if isinstance(tokens, str):
            return generate_llm_output(tokens)
        return generate_llm_output("Default Name: Default, Skills: Default")


# --- IBM Granite Model Loading (MOCK FALLBACK) ---

tokenizer = None
model = None

try:
    tokenizer = AutoTokenizer.from_pretrained("ibm-granite/granite-3.3-2b-instruct")
    model = AutoModelForCausalLM.from_pretrained("ibm-granite/granite-3.3-2b-instruct")
    print("SUCCESS: Loaded IBM Granite model.")
except Exception as e:
    print(f"Warning: Could not load Granite model. Using DUMMY/MOCK function. Error: {e}")
    model = MockModel()
    tokenizer = MockTokenizer()


# --- AUTHENTICATION FUNCTIONS (UNCHANGED) ---

def register_user(username, password, role):
    if not username or not password or not role:
        return "❌ Registration failed: All fields are required.", gr.update(value=""), gr.update(value=""), gr.update(value=None), gr.update(value=""), gr.update(value="")
               
    username = username.strip()
    password = password.strip()
    
    if username in USER_DB:
        return f"❌ Registration failed: User '{username}' already exists.", gr.update(value=""), gr.update(value=""), gr.update(value=None), gr.update(value=""), gr.update(value="")
    
    USER_DB[username] = {"password": password, "role": role}
    
    return f"✅ Success! User '{username}' registered as **{role.upper()}**. Please proceed to the Login section.", gr.update(value=""), gr.update(value=""), gr.update(value=None), gr.update(value=""), gr.update(value="")


def user_login(username, password):
    username = username.strip()
    password = password.strip()
    
    if username in USER_DB:
        if USER_DB[username]["password"] == password:
            role = USER_DB[username]["role"]
            
            if role == "student":
                # When student logs in, update job list
                job_ids = list(JOB_POSTINGS.keys())
                job_markdown = view_jobs_markdown()
                
                return (username, role), f"✅ Login Success! Welcome, {username} ({role.upper()}).", gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), gr.update(choices=job_ids), gr.update(value=job_markdown)
            elif role == "hr":
                return (username, role), f"✅ Login Success! Welcome, {username} ({role.upper()}).", gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), gr.update(choices=[]), gr.update(value="")
        else:
            return (None, "guest"), "❌ Login Failed: Invalid password.", gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), gr.update(choices=[]), gr.update(value="")
    else:
        return (None, "guest"), "❌ Login Failed: Invalid username or password.", gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), gr.update(choices=[]), gr.update(value="")

def user_logout():
    return (None, "guest"), "👋 Logged out. Please log in again.", gr.update(visible=False), gr.update(visible=False), gr.update(visible=True)


# --- CORE FUNCTIONALITY (RESUME GENERATION - UNCHANGED FROM PREVIOUS STEP) ---

def generate_resume(name, email_id, contact_no, linkedin_url, objective, skills, education, experience, projects_input, certifications_input, prompt_extra):
    """Generates the AI text and the DOCX file with all fields from divya_resume.pdf."""
    
    if not name or not skills or not education:
        return "❌ Error: Please fill in Full Name, Key Skills, and Education to generate a resume.", "💡 No guidance available. Fill in required fields.", None
    
    safe_name = re.sub(r'[^a-zA-Z0-9_]', '', name.replace(' ', '_'))
    file_path = f"Professional_Resume_{safe_name}_{int(time.time())}.docx"

    # The prompt is used to get the AI-generated text output
    prompt = f"""Generate a clean, professional resume text for:
Name: {name}
Skills: {skills}
Education: {education}
Experience: {experience}
{prompt_extra if prompt_extra else ""}
Ensure the structure includes Summary, Skills, Education, Experience, and Certifications.
"""

    try:
        # --- Model generation logic (Robust for mock/real) ---
        if isinstance(model, MockModel):
            outputs = model.generate(prompt, max_new_tokens=400, num_return_sequences=1)
            raw_text = tokenizer.decode(outputs, skip_special_tokens=True) 
        else:
            inputs = tokenizer(prompt, return_tensors="pt")["input_ids"]
            outputs = model.generate(inputs, max_length=600, num_return_sequences=1)
            raw_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

        resume_text = raw_text.replace(prompt, "").strip()
        resume_text = re.sub(r"<.*?>", "", resume_text).strip()
        if not resume_text:
            resume_text = generate_llm_output(prompt)
                
        
        # --- Create Word document with EXTENDED STRUCTURE to match the PDF ---
        doc = Document()
        
        # 1. HEADER (NAME and Contact Details)
        name_p = doc.add_paragraph(name.upper())
        name_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Use the provided contact fields directly
        contact_p = doc.add_paragraph(
            f"Email id: {email_id} | Contact no: {contact_no} | LinkedIn: {linkedin_url}"
        )
        contact_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # 2. CAREER OBJECTIVE
        doc.add_heading("CAREER OBJECTIVE", level=1)
        objective_text = objective if objective.strip() else "To leverage my skills in programming, data analysis, and problem-solving to contribute to innovative projects and achieve professional growth in a dynamic environment."
        doc.add_paragraph(objective_text)
        
        # 3. EDUCATION
        doc.add_heading("EDUCATION", level=1)
        doc.add_paragraph(education)
        
        # 4. SKILLS (Manually structured, using user's input for Programming Languages)
        doc.add_heading("SKILLS", level=1)
        doc.add_paragraph(
            f"Programming Languages: {skills} \n"
            f"Frontend Technologies: HTML5, CSS3, Bootstrap \n"
            f"Database: SQL \n"
            f"Soft Skills: Teamwork, Problem-solving." 
        )
        
        # 5. INTERNSHIPS (Using the 'Experience' input field content)
        doc.add_heading("INTERNSHIPS", level=1)
        if experience.lower().strip() not in ["none", ""]:
            doc.add_paragraph(experience) 
        else:
            doc.add_paragraph("No formal internships or major experience listed.")
            
        # 6. PROJECTS 
        doc.add_heading("PROJECTS", level=1)
        if projects_input.lower().strip() not in ["none", ""]:
            doc.add_paragraph(projects_input)
        else:
            doc.add_paragraph("• Loan Approval Analytics: A Classification-Based Data Mining Approach\n• Smart SDLC AI-Enhanced Software Development Life Cycle")
        
        # 7. CERTIFICATIONS 
        doc.add_heading("CERTIFICATIONS", level=1)
        if certifications_input.lower().strip() not in ["none", ""]:
            doc.add_paragraph(certifications_input)
        else:
            doc.add_paragraph("• Python Basics for Data Science - IBM\n• NPTEL certification in Social Networks\n• Generative AI with IBM Cloud - Smartinternz")

        doc.save(file_path)

        guidance = f"""
### 💡 Resume Enhancement Tips:
- **Tailor:** Did you mention skills specific to the job you are applying for?
- **Metrics:** Use numbers to quantify your achievements (e.g., *Reduced costs by 15%*).
- **File:** Your DOCX file, **{file_path}**, is ready for download.
"""
        
        return resume_text, guidance, file_path
    
    except Exception as e:
        error_msg = f"❌ Resume Generation Failed: An unexpected error occurred.\nError: {type(e).__name__}: {str(e)}"
        print(error_msg)
        return error_msg, f"💡 An error occurred during processing. Please check your inputs. The generated file was not saved to: {file_path}", None


# --- HR JOB POSTING FUNCTIONS (MODIFIED to use more distinct ID) ---

def post_job(title, company, description):
    if not title or not company or not description:
        # Also return outputs for job_dropdown and job_context to maintain flow
        return gr.update(value=title), gr.update(value=company), gr.update(value=description), view_jobs_markdown(), f"❌ Error: All job fields are required to post.", gr.update(choices=list(JOB_POSTINGS.keys()), value=None)

    # Use a more distinct Job ID format
    job_id = f"{company.upper()[:3]}-{random.randint(100, 999)}-{int(time.time()) % 1000}"
    JOB_POSTINGS[job_id] = {
        "title": title,
        "company": company,
        "description": description,
        "posted_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    job_keys = list(JOB_POSTINGS.keys())
    
    return gr.update(value=""), gr.update(value=""), gr.update(value=""), view_jobs_markdown(), f"✅ Success! Job **'{title}'** posted with ID: **{job_id}**", gr.update(choices=job_keys)

def view_jobs_markdown():
    if not JOB_POSTINGS:
        return "No job postings available at this time."
        
    job_list_markdown = "### Available Job Openings\n"
    for jid, job in JOB_POSTINGS.items():
        job_list_markdown += f"#### {job['title']} at {job['company']}\n"
        job_list_markdown += f"**ID:** `{jid}` | **Posted:** {job['posted_at']}\n"
        truncated_desc = job['description'][:150].replace('\n', ' ') + ("..." if len(job['description']) > 150 else "")
        job_list_markdown += f"{truncated_desc}\n\n"
    return job_list_markdown


# --- APPLICANT INTERACTION FUNCTIONS (NEW) ---

def select_job_details(job_id):
    """Returns the full description for a selected job."""
    if job_id and job_id in JOB_POSTINGS:
        job = JOB_POSTINGS[job_id]
        details = (
            f"### {job['title']} at {job['company']}\n"
            f"**Job ID:** {job_id}\n"
            f"**Posted:** {job['posted_at']}\n\n"
            f"**Description:**\n{job['description']}"
        )
        # Enable apply button and clear status
        return details, gr.update(visible=True), ""
    # Clear description, hide button
    return "Please select a job ID to view the full description and apply.", gr.update(visible=False), ""

def apply_for_job(job_id, auth_state_tuple):
    """Mocks the application process."""
    user = auth_state_tuple[0]
    
    if not user:
        return "❌ **Application Failed**: You must be logged in as a student to apply."
    
    if not job_id or job_id not in JOB_POSTINGS:
        return "❌ **Application Failed**: Please select a valid job first."
        
    job_title = JOB_POSTINGS[job_id]['title']
    
    # In a real system, this is where the application logic and resume submission would go.
    
    return f"✅ **Application Successful!**\n\n**{user}** has successfully applied for **{job_title}** (ID: {job_id}). Your resume (if generated) will be sent for review. Good luck! 🤞"


# --- GRADIO INTERFACE SETUP ---

custom_css = """
.gradio-container { background: #f0f0f0; }
.textbox-bordered { border: 3px solid #1E3A8A; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.2); }
.custom-run-button { background-color: #0072CE !important; color: white !important; font-weight: bold; border-radius: 8px; padding: 10px 20px; }
.hr-header { color: #D61B1F; font-size: 1.5em; font-weight: bold; }
.applicant-header { color: #0072CE; font-size: 1.5em; font-weight: bold; }
.auth-title { color: #1E3A8A; font-size: 2em; }
"""

with gr.Blocks(css=custom_css) as demo:
    
    # --- State Variables ---
    auth_state = gr.State((None, "guest"))
    
    gr.Markdown("# 🏢 IBM Granite AI Career Portal")

    # 1. Define all Components
    with gr.Tabs() as main_tabs:
        
        # --- TAB 1: LOGIN / REGISTER ---
        with gr.TabItem("Authentication", elem_id="auth_tab") as auth_tab:
            gr.Markdown("<div class='auth-title'>Access Portal</div>")
            login_status_msg = gr.Markdown("Please login or register to use the portals.")
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 📝 New User Registration")
                    reg_user = gr.Textbox(label="Username")
                    reg_pass = gr.Textbox(label="Password", type="password")
                    reg_role = gr.Radio(["student", "hr"], label="Account Type")
                    register_btn = gr.Button("Register Account", variant="secondary")
                    reg_message = gr.Markdown("")
                    
                with gr.Column(scale=1):
                    gr.Markdown("### 🔑 Existing User Login")
                    login_user = gr.Textbox(label="Username")
                    login_pass = gr.Textbox(label="Password", type="password")
                    login_btn = gr.Button("Login to Portal", variant="primary")
        
        # --- TAB 2: APPLICANT PORTAL (Updated with all fields AND Job Application) ---
        with gr.TabItem("Applicant Portal", visible=False) as applicant_tab:
            
            gr.Markdown("<div class='applicant-header'>AI Resume Generation & Job Application</div>")
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 👤 Personal Details & Resume Builder")
                    # Fields from Divya_Resume.pdf
                    name = gr.Textbox(label="Full Name", value="Divya Tadisetti")
                    with gr.Row():
                        email_id = gr.Textbox(label="Email id", value="dtadisetti8@gmail.com")
                        contact_no = gr.Textbox(label="Contact no", value="9989059362")
                    linkedin_url = gr.Textbox(label="LinkedIn URL", value="divya-tadisetti-161336304")
                    gr.Markdown("---")
                    objective = gr.Textbox(label="Career Objective", lines=3, placeholder="To leverage my skills...", value="To leverage my skills in programming, data analysis, and problem-solving to contribute to innovative projects and achieve professional growth in a dynamic environment.")
                    skills = gr.Textbox(label="Key Skills (Programming/Tech)", value="C, Python, Java, HTML5, CSS3, Bootstrap, SQL")
                    education = gr.Textbox(label="Education", lines=2, value="Seshadri Rao Gudlavalleru Engineering College, BTech in Computer Science and Engineering | GPA: 9.20 | 2026")
                    gr.Markdown("---")
                    experience = gr.Textbox(label="Internships / Experience", lines=3, placeholder="List your internships and professional roles here.", value="Cyber security AIMER Society (July-2024): Learned threat detection and risk assessment; Generative Al with IBM Cloud- Smartinternz(July -2025): Built small-scale Al model deployment project")
                    projects_input = gr.Textbox(label="Projects", lines=3, placeholder="Separate projects with a new line or bullet points.", value="Loan Approval Analytics: A Classification-Based Data Mining Approach; Smart SDLC AI-Enhanced Software Development Life Cycle")
                    certifications_input = gr.Textbox(label="Certifications", lines=2, placeholder="List certifications separated by new lines.", value="Python Basics for Data Science - IBM; NPTEL certification in Social Networks")
                    gr.Markdown("---")
                    prompt_extra = gr.Textbox(label="Additional Instructions for AI", lines=1, placeholder="e.g., Focus on leadership skills for a managerial role.", value="NONE") 
                    run = gr.Button("✨ Generate Professional Resume", elem_classes=["custom-run-button"])
                
                with gr.Column(scale=2):
                    gr.Markdown("### Resume Output")
                    with gr.Tab("AI Generated Text"):
                        resume_out = gr.Textbox(label="📄 Review AI Generated Text (LLM Raw Output)", lines=10, elem_classes=["textbox-bordered"])
                    with gr.Tab("Guidance"):
                        guidance_out = gr.Markdown("💡 Guidance and Tips will appear here after generation.")
                    
                    download = gr.File(label="⬇️ Download Formatted .docx File")
            
            # --- JOB APPLICATION SECTION (MODIFIED AS REQUESTED) ---
            gr.Markdown("---")
            gr.Markdown("### 🚀 Job Application Center")
            
            with gr.Row():
                with gr.Column(scale=1):
                    job_summary = gr.Markdown(view_jobs_markdown(), label="Job Summary List")
                    
                with gr.Column(scale=2):
                    gr.Markdown("#### Select a Job ID to view the full description")
                    job_dropdown = gr.Dropdown(
                        choices=[], # Dynamic choices
                        label="Select Job ID",
                        interactive=True
                    )
                    
                    job_description_out = gr.Markdown("Select a job ID from the dropdown to view the description.")
                    
                    # Application Button
                    apply_btn = gr.Button("🚀 Apply for Selected Job", variant="primary", visible=False)
                    apply_status = gr.Markdown("Application status will appear here.")
                    
            logout_btn_applicant = gr.Button("Logout", variant="secondary")

        # --- TAB 3: HR PORTAL (Unchanged Structure) ---
        with gr.TabItem("HR Portal", visible=False) as hr_tab:
            
            gr.Markdown("<div class='hr-header'>HR Management Portal: Post New Job Applications</div>")
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 📋 Post New Job")
                    job_title = gr.Textbox(label="Job Title", placeholder="e.g., Senior Data Scientist")
                    job_company = gr.Textbox(label="Company Name", placeholder="e.g., IBM")
                    job_description = gr.Textbox(label="Job Description", lines=5, placeholder="Paste the full job description here.")
                    post_btn = gr.Button("Post Job", variant="primary")
                    posting_message = gr.Markdown("Job posting status will appear here.")
                    
                with gr.Column(scale=2):
                    gr.Markdown("### 📜 Current Active Job Postings")
                    current_jobs_out = gr.Markdown(view_jobs_markdown(), visible=True)

            logout_btn_hr = gr.Button("Logout", variant="secondary")
            
    
    # 2. Define all Event Handlers (Click functions)

    # --- Registration Logic (Unchanged) ---
    register_btn.click(
        register_user,
        inputs=[reg_user, reg_pass, reg_role],
        outputs=[reg_message, reg_user, reg_pass, reg_role, login_user, login_pass]
    )
    
    # --- Login Logic (MODIFIED to update job list on student login) ---
    login_btn.click(
        user_login,
        inputs=[login_user, login_pass],
        outputs=[auth_state, login_status_msg, applicant_tab, hr_tab, auth_tab, job_dropdown, job_summary]
    )

    # --- Applicant Resume Generation Logic (Unchanged inputs) ---
    run.click(
        generate_resume,
        inputs=[
            name, email_id, contact_no, linkedin_url, objective, skills, 
            education, experience, projects_input, certifications_input, prompt_extra
        ],
        outputs=[resume_out, guidance_out, download] 
    )
    
    # --- Job Interaction Logic (NEW) ---
    job_dropdown.change(
        select_job_details,
        inputs=[job_dropdown],
        outputs=[job_description_out, apply_btn, apply_status]
    )
    
    apply_btn.click(
        apply_for_job,
        inputs=[job_dropdown, auth_state],
        outputs=[apply_status]
    )
    
    # --- HR Post Job Logic (MODIFIED to update job lists in both portals) ---
    post_btn.click(
        post_job,
        inputs=[job_title, job_company, job_description],
        # Update HR display, post message, and Applicant Dropdown
        outputs=[job_title, job_company, job_description, current_jobs_out, posting_message, job_dropdown]
    ).then(
        view_jobs_markdown, 
        inputs=[],
        # Update Applicant Summary list
        outputs=[job_summary] 
    )
    
    # --- LOGOUT Logic (Shared) ---
    logout_btn_applicant.click(
        user_logout,
        inputs=[],
        outputs=[auth_state, login_status_msg, applicant_tab, hr_tab, auth_tab]
    )
    
    logout_btn_hr.click(
        user_logout,
        inputs=[],
        outputs=[auth_state, login_status_msg, applicant_tab, hr_tab, auth_tab]
    )

demo.launch()'''

# pip install gradio transformers python-docx
'''
import gradio as gr
from transformers import AutoTokenizer, AutoModelForCausalLM
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import re
import os
import time
import random 

# --- MOCK DATABASE AND STATE ---
USER_DB = {
    "test_hr": {"password": "hr_password", "role": "hr"},
    "test_student": {"password": "student_password", "role": "student"}
}
JOB_POSTINGS = {} 

# --- MOCK IMPLEMENTATION DEFINITION ---
def generate_llm_output(prompt):
    """Generates a structured mock AI response."""
    name_match = re.search(r"Name: (.*)", prompt)
    skills_match = re.search(r"Skills: (.*)", prompt)
    name = name_match.group(1).strip() if name_match else "Applicant Name"
    skills = skills_match.group(1).strip() if skills_match else "Python, Leadership, SQL"
    
    return f"***DUMMY AI RESPONSE***\n\n**SUMMARY:** Highly motivated individual ({name}) with a strong foundation in {skills}. Proven ability to tackle complex challenges and drive results.\n\n**SKILLS:** {skills}\n\n**EXPERIENCE:** Simulated job experience here, demonstrating proficiency in key skills.\n\n**EDUCATION:** University details here."

class MockModel:
    def generate(self, input_ids, max_new_tokens, num_return_sequences):
        return {"input_ids": input_ids} 

class MockTokenizer:
    def __init__(self): self.eos_token = ""
    def __call__(self, text, *args, **kwargs): return {"input_ids": text}
    def decode(self, tokens, skip_special_tokens=True): 
        if isinstance(tokens, dict) and "input_ids" in tokens:
            tokens = tokens["input_ids"]
        if isinstance(tokens, str):
            return generate_llm_output(tokens)
        return generate_llm_output("Default Name: Default, Skills: Default")


# --- IBM Granite Model Loading (MOCK FALLBACK) ---

tokenizer = None
model = None

try:
    tokenizer = AutoTokenizer.from_pretrained("ibm-granite/granite-3.3-2b-instruct")
    model = AutoModelForCausalLM.from_pretrained("ibm-granite/granite-3.3-2b-instruct")
    print("SUCCESS: Loaded IBM Granite model.")
except Exception as e:
    print(f"Warning: Could not load Granite model. Using DUMMY/MOCK function. Error: {e}")
    model = MockModel()
    tokenizer = MockTokenizer()


# --- AUTHENTICATION FUNCTIONS (UNCHANGED) ---

def register_user(username, password, role):
    if not username or not password or not role:
        return "❌ Registration failed: All fields are required.", gr.update(value=""), gr.update(value=""), gr.update(value=None), gr.update(value=""), gr.update(value="")
               
    username = username.strip()
    password = password.strip()
    
    if username in USER_DB:
        return f"❌ Registration failed: User '{username}' already exists.", gr.update(value=""), gr.update(value=""), gr.update(value=None), gr.update(value=""), gr.update(value="")
    
    USER_DB[username] = {"password": password, "role": role}
    
    return f"✅ Success! User '{username}' registered as **{role.upper()}**. Please proceed to the Login section.", gr.update(value=""), gr.update(value=""), gr.update(value=None), gr.update(value=""), gr.update(value="")


def user_login(username, password):
    username = username.strip()
    password = password.strip()
    
    if username in USER_DB:
        if USER_DB[username]["password"] == password:
            role = USER_DB[username]["role"]
            
            if role == "student":
                job_ids = list(JOB_POSTINGS.keys())
                job_markdown = view_jobs_markdown()
                
                # Note: The logic for updating job_dropdown and job_summary remains here
                return (username, role), f"✅ Login Success! Welcome, {username} ({role.upper()}).", gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), gr.update(choices=job_ids), gr.update(value=job_markdown)
            elif role == "hr":
                return (username, role), f"✅ Login Success! Welcome, {username} ({role.upper()}).", gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), gr.update(choices=[]), gr.update(value="")
        else:
            return (None, "guest"), "❌ Login Failed: Invalid password.", gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), gr.update(choices=[]), gr.update(value="")
    else:
        return (None, "guest"), "❌ Login Failed: Invalid username or password.", gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), gr.update(choices=[]), gr.update(value="")

def user_logout():
    return (None, "guest"), "👋 Logged out. Please log in again.", gr.update(visible=False), gr.update(visible=False), gr.update(visible=True)


# --- CORE FUNCTIONALITY (RESUME GENERATION - UNCHANGED) ---

def generate_resume(name, email_id, contact_no, linkedin_url, objective, skills, education, experience, projects_input, certifications_input, prompt_extra):
    """Generates the AI text and the DOCX file with all fields from divya_resume.pdf."""
    
    if not name or not skills or not education:
        return "❌ Error: Please fill in Full Name, Key Skills, and Education to generate a resume.", "💡 No guidance available. Fill in required fields.", None
    
    safe_name = re.sub(r'[^a-zA-Z0-9_]', '', name.replace(' ', '_'))
    file_path = f"Professional_Resume_{safe_name}_{int(time.time())}.docx"

    prompt = f"""Generate a clean, professional resume text for:
Name: {name}
Skills: {skills}
Education: {education}
Experience: {experience}
{prompt_extra if prompt_extra else ""}
Ensure the structure includes Summary, Skills, Education, Experience, and Certifications.
"""

    try:
        # --- Model generation logic (Robust for mock/real) ---
        if isinstance(model, MockModel):
            outputs = model.generate(prompt, max_new_tokens=400, num_return_sequences=1)
            raw_text = tokenizer.decode(outputs, skip_special_tokens=True) 
        else:
            inputs = tokenizer(prompt, return_tensors="pt")["input_ids"]
            outputs = model.generate(inputs, max_length=600, num_return_sequences=1)
            raw_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

        resume_text = raw_text.replace(prompt, "").strip()
        resume_text = re.sub(r"<.*?>", "", resume_text).strip()
        if not resume_text:
            resume_text = generate_llm_output(prompt)
                
        
        # --- Create Word document with EXTENDED STRUCTURE to match the PDF ---
        doc = Document()
        
        # 1. HEADER (NAME and Contact Details)
        name_p = doc.add_paragraph(name.upper())
        name_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        contact_p = doc.add_paragraph(
            f"Email id: {email_id} | Contact no: {contact_no} | LinkedIn: {linkedin_url}"
        )
        contact_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # 2. CAREER OBJECTIVE
        doc.add_heading("CAREER OBJECTIVE", level=1)
        objective_text = objective if objective.strip() else "To leverage my skills in programming, data analysis, and problem-solving to contribute to innovative projects and achieve professional growth in a dynamic environment."
        doc.add_paragraph(objective_text)
        
        # 3. EDUCATION
        doc.add_heading("EDUCATION", level=1)
        doc.add_paragraph(education)
        
        # 4. SKILLS
        doc.add_heading("SKILLS", level=1)
        doc.add_paragraph(
            f"Programming Languages: {skills} \n"
            f"Frontend Technologies: HTML5, CSS3, Bootstrap \n"
            f"Database: SQL \n"
            f"Soft Skills: Teamwork, Problem-solving." 
        )
        
        # 5. INTERNSHIPS
        doc.add_heading("INTERNSHIPS", level=1)
        if experience.lower().strip() not in ["none", ""]:
            doc.add_paragraph(experience) 
        else:
            doc.add_paragraph("No formal internships or major experience listed.")
            
        # 6. PROJECTS 
        doc.add_heading("PROJECTS", level=1)
        if projects_input.lower().strip() not in ["none", ""]:
            doc.add_paragraph(projects_input)
        else:
            doc.add_paragraph("• Loan Approval Analytics: A Classification-Based Data Mining Approach\n• Smart SDLC AI-Enhanced Software Development Life Cycle")
        
        # 7. CERTIFICATIONS 
        doc.add_heading("CERTIFICATIONS", level=1)
        if certifications_input.lower().strip() not in ["none", ""]:
            doc.add_paragraph(certifications_input)
        else:
            doc.add_paragraph("• Python Basics for Data Science - IBM\n• NPTEL certification in Social Networks\n• Generative AI with IBM Cloud - Smartinternz")

        doc.save(file_path)

        guidance = f"""
### 💡 Resume Enhancement Tips:
- **Tailor:** Did you mention skills specific to the job you are applying for?
- **Metrics:** Use numbers to quantify your achievements (e.g., *Reduced costs by 15%*).
- **File:** Your DOCX file, **{file_path}**, is ready for download.
"""
        
        return resume_text, guidance, file_path
    
    except Exception as e:
        error_msg = f"❌ Resume Generation Failed: An unexpected error occurred.\nError: {type(e).__name__}: {str(e)}"
        print(error_msg)
        return error_msg, f"💡 An error occurred during processing. Please check your inputs. The generated file was not saved to: {file_path}", None


# --- HR JOB POSTING FUNCTIONS (MODIFIED to use more distinct ID) ---

def post_job(title, company, description):
    if not title or not company or not description:
        # Include job_dropdown choices update to maintain consistent outputs across calls
        return gr.update(value=title), gr.update(value=company), gr.update(value=description), view_jobs_markdown(), f"❌ Error: All job fields are required to post.", gr.update(choices=list(JOB_POSTINGS.keys()), value=None)

    job_id = f"{company.upper()[:3]}-{random.randint(100, 999)}-{int(time.time()) % 1000}"
    JOB_POSTINGS[job_id] = {
        "title": title,
        "company": company,
        "description": description,
        "posted_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    job_keys = list(JOB_POSTINGS.keys())
    
    return gr.update(value=""), gr.update(value=""), gr.update(value=""), view_jobs_markdown(), f"✅ Success! Job **'{title}'** posted with ID: **{job_id}**", gr.update(choices=job_keys)

def view_jobs_markdown():
    if not JOB_POSTINGS:
        return "No job postings available at this time."
        
    job_list_markdown = "### Available Job Openings\n"
    for jid, job in JOB_POSTINGS.items():
        job_list_markdown += f"#### {job['title']} at {job['company']}\n"
        job_list_markdown += f"**ID:** `{jid}` | **Posted:** {job['posted_at']}\n"
        truncated_desc = job['description'][:150].replace('\n', ' ') + ("..." if len(job['description']) > 150 else "")
        job_list_markdown += f"{truncated_desc}\n\n"
    return job_list_markdown


# --- APPLICANT INTERACTION FUNCTION (SIMPLIFIED) ---

def select_job_details(job_id):
    """Returns the full description for a selected job."""
    if job_id and job_id in JOB_POSTINGS:
        job = JOB_POSTINGS[job_id]
        details = (
            f"### {job['title']} at {job['company']}\n"
            f"**Job ID:** {job_id}\n"
            f"**Posted:** {job['posted_at']}\n\n"
            f"**Description:**\n{job['description']}"
        )
        return details
    return "Please select a job ID to view the full description."


# --- GRADIO INTERFACE SETUP ---

custom_css = """
.gradio-container { background: #f0f0f0; }
.textbox-bordered { border: 3px solid #1E3A8A; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.2); }
.custom-run-button { background-color: #0072CE !important; color: white !important; font-weight: bold; border-radius: 8px; padding: 10px 20px; }
.hr-header { color: #D61B1F; font-size: 1.5em; font-weight: bold; }
.applicant-header { color: #0072CE; font-size: 1.5em; font-weight: bold; }
.auth-title { color: #1E3A8A; font-size: 2em; }
"""

with gr.Blocks(css=custom_css) as demo:
    
    # --- State Variables ---
    auth_state = gr.State((None, "guest"))
    
    gr.Markdown("# 🏢 IBM Granite AI Career Portal")

    # 1. Define all Components
    with gr.Tabs() as main_tabs:
        
        # --- TAB 1: LOGIN / REGISTER (Unchanged) ---
        with gr.TabItem("Authentication", elem_id="auth_tab") as auth_tab:
            gr.Markdown("<div class='auth-title'>Access Portal</div>")
            login_status_msg = gr.Markdown("Please login or register to use the portals.")
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 📝 New User Registration")
                    reg_user = gr.Textbox(label="Username")
                    reg_pass = gr.Textbox(label="Password", type="password")
                    reg_role = gr.Radio(["student", "hr"], label="Account Type")
                    register_btn = gr.Button("Register Account", variant="secondary")
                    reg_message = gr.Markdown("")
                    
                with gr.Column(scale=1):
                    gr.Markdown("### 🔑 Existing User Login")
                    login_user = gr.Textbox(label="Username")
                    login_pass = gr.Textbox(label="Password", type="password")
                    login_btn = gr.Button("Login to Portal", variant="primary")
        
        # --- TAB 2: APPLICANT PORTAL (Job Application Section Modified) ---
        with gr.TabItem("Applicant Portal", visible=False) as applicant_tab:
            
            gr.Markdown("<div class='applicant-header'>AI Resume Generation & Job Details</div>")
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 👤 Personal Details & Resume Builder")
                    name = gr.Textbox(label="Full Name")
                    with gr.Row():
                        email_id = gr.Textbox(label="Email id")
                        contact_no = gr.Textbox(label="Contact no")
                    linkedin_url = gr.Textbox(label="LinkedIn URL")
                    gr.Markdown("---")
                    objective = gr.Textbox(label="Career Objective", lines=3, placeholder="To leverage my skills...")
                    skills = gr.Textbox(label="Key Skills (Programming/Tech)")
                    education = gr.Textbox(label="Education", lines=2)
                    gr.Markdown("---")
                    experience = gr.Textbox(label="Internships / Experience", lines=3, placeholder="List your internships and professional roles here.")
                    projects_input = gr.Textbox(label="Projects", lines=3, placeholder="Separate projects with a new line or bullet points.")
                    certifications_input = gr.Textbox(label="Certifications", lines=2, placeholder="List certifications separated by new lines.")
                    gr.Markdown("---")
                    prompt_extra = gr.Textbox(label="Additional Instructions for AI", lines=1, placeholder="e.g., Focus on leadership skills for a managerial role.") 
                    run = gr.Button("✨ Generate Professional Resume", elem_classes=["custom-run-button"])
                
                with gr.Column(scale=2):
                    gr.Markdown("### Resume Output")
                    with gr.Tab("AI Generated Text"):
                        resume_out = gr.Textbox(label="📄 Review AI Generated Text (LLM Raw Output)", lines=10, elem_classes=["textbox-bordered"])
                    with gr.Tab("Guidance"):
                        guidance_out = gr.Markdown("💡 Guidance and Tips will appear here after generation.")
                    
                    download = gr.File(label="⬇️ Download Formatted .docx File")
            
            # --- JOB DETAILS SECTION (SIMPLIFIED AS REQUESTED) ---
            gr.Markdown("---")
            gr.Markdown("### 📜 Job Listing Details")
            
            with gr.Row():
                with gr.Column(scale=1):
                    job_summary = gr.Markdown(view_jobs_markdown(), label="Job Summary List")
                    
                with gr.Column(scale=2):
                    gr.Markdown("#### Select a Job ID to view the full description")
                    job_dropdown = gr.Dropdown(
                        choices=[], 
                        label="Select Job ID",
                        interactive=True
                    )
                    
                    # Only the description output remains
                    job_description_out = gr.Markdown("Select a job ID from the dropdown to view the description.")
                    
            logout_btn_applicant = gr.Button("Logout", variant="secondary")

        # --- TAB 3: HR PORTAL (Unchanged) ---
        with gr.TabItem("HR Portal", visible=False) as hr_tab:
            
            gr.Markdown("<div class='hr-header'>HR Management Portal: Post New Job Applications</div>")
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 📋 Post New Job")
                    job_title = gr.Textbox(label="Job Title", placeholder="e.g., Senior Data Scientist")
                    job_company = gr.Textbox(label="Company Name", placeholder="e.g., IBM")
                    job_description = gr.Textbox(label="Job Description", lines=5, placeholder="Paste the full job description here.")
                    post_btn = gr.Button("Post Job", variant="primary")
                    posting_message = gr.Markdown("Job posting status will appear here.")
                    
                with gr.Column(scale=2):
                    gr.Markdown("### 📜 Current Active Job Postings")
                    current_jobs_out = gr.Markdown(view_jobs_markdown(), visible=True)

            logout_btn_hr = gr.Button("Logout", variant="secondary")
            
    
    # 2. Define all Event Handlers (Click functions)

    # --- Registration Logic (Unchanged) ---
    register_btn.click(
        register_user,
        inputs=[reg_user, reg_pass, reg_role],
        outputs=[reg_message, reg_user, reg_pass, reg_role, login_user, login_pass]
    )
    
    # --- Login Logic (Modified output for job components) ---
    login_btn.click(
        user_login,
        inputs=[login_user, login_pass],
        outputs=[auth_state, login_status_msg, applicant_tab, hr_tab, auth_tab, job_dropdown, job_summary]
    )

    # --- Applicant Resume Generation Logic (Unchanged) ---
    run.click(
        generate_resume,
        inputs=[
            name, email_id, contact_no, linkedin_url, objective, skills, 
            education, experience, projects_input, certifications_input, prompt_extra
        ],
        outputs=[resume_out, guidance_out, download] 
    )
    
    # --- Job Interaction Logic (SIMPLIFIED) ---
    job_dropdown.change(
        select_job_details,
        inputs=[job_dropdown],
        outputs=[job_description_out] # Only outputs the description
    )
    
    # --- HR Post Job Logic (Modified output for job components) ---
    post_btn.click(
        post_job,
        inputs=[job_title, job_company, job_description],
        # Update HR display, post message, and Applicant Dropdown
        outputs=[job_title, job_company, job_description, current_jobs_out, posting_message, job_dropdown]
    ).then(
        view_jobs_markdown, 
        inputs=[],
        # Update Applicant Summary list
        outputs=[job_summary] 
    )
    
    # --- LOGOUT Logic (Shared) ---
    logout_btn_applicant.click(
        user_logout,
        inputs=[],
        outputs=[auth_state, login_status_msg, applicant_tab, hr_tab, auth_tab]
    )
    
    logout_btn_hr.click(
        user_logout,
        inputs=[],
        outputs=[auth_state, login_status_msg, applicant_tab, hr_tab, auth_tab]
    )

demo.launch()'''

# pip install gradio transformers python-docx
'''
import gradio as gr
from transformers import AutoTokenizer, AutoModelForCausalLM
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import re
import os
import time
import random 

# --- MOCK DATABASE AND STATE ---
USER_DB = {
    "test_hr": {"password": "hr_password", "role": "hr"},
    "test_student": {"password": "student_password", "role": "student"}
}
JOB_POSTINGS = {} 

# --- MOCK IMPLEMENTATION DEFINITION ---
def generate_llm_output(prompt):
    """Generates a structured mock AI response."""
    name_match = re.search(r"Name: (.*)", prompt)
    skills_match = re.search(r"Skills: (.*)", prompt)
    name = name_match.group(1).strip() if name_match else "Applicant Name"
    skills = skills_match.group(1).strip() if skills_match else "Python, Leadership, SQL"
    
    return f"***DUMMY AI RESPONSE***\n\n**SUMMARY:** Highly motivated individual ({name}) with a strong foundation in {skills}. Proven ability to tackle complex challenges and drive results.\n\n**SKILLS:** {skills}\n\n**EXPERIENCE:** Simulated job experience here, demonstrating proficiency in key skills.\n\n**EDUCATION:** University details here."

class MockModel:
    def generate(self, input_ids, max_new_tokens, num_return_sequences):
        return {"input_ids": input_ids} 

class MockTokenizer:
    def __init__(self): self.eos_token = ""
    def __call__(self, text, *args, **kwargs): return {"input_ids": text}
    def decode(self, tokens, skip_special_tokens=True): 
        if isinstance(tokens, dict) and "input_ids" in tokens:
            tokens = tokens["input_ids"]
        if isinstance(tokens, str):
            return generate_llm_output(tokens)
        return generate_llm_output("Default Name: Default, Skills: Default")


# --- IBM Granite Model Loading (MOCK FALLBACK) ---

tokenizer = None
model = None

try:
    tokenizer = AutoTokenizer.from_pretrained("ibm-granite/granite-3.3-2b-instruct")
    model = AutoModelForCausalLM.from_pretrained("ibm-granite/granite-3.3-2b-instruct")
    print("SUCCESS: Loaded IBM Granite model.")
except Exception as e:
    print(f"Warning: Could not load Granite model. Using DUMMY/MOCK function. Error: {e}")
    model = MockModel()
    tokenizer = MockTokenizer()


# --- AUTHENTICATION FUNCTIONS (UNCHANGED) ---

def register_user(username, password, role):
    if not username or not password or not role:
        return "❌ Registration failed: All fields are required.", gr.update(value=""), gr.update(value=""), gr.update(value=None), gr.update(value=""), gr.update(value="")
               
    username = username.strip()
    password = password.strip()
    
    if username in USER_DB:
        return f"❌ Registration failed: User '{username}' already exists.", gr.update(value=""), gr.update(value=""), gr.update(value=None), gr.update(value=""), gr.update(value="")
    
    USER_DB[username] = {"password": password, "role": role}
    
    return f"✅ Success! User '{username}' registered as **{role.upper()}**. Please proceed to the Login section.", gr.update(value=""), gr.update(value=""), gr.update(value=None), gr.update(value=""), gr.update(value="")


def user_login(username, password):
    username = username.strip()
    password = password.strip()
    
    if username in USER_DB:
        if USER_DB[username]["password"] == password:
            role = USER_DB[username]["role"]
            
            if role == "student":
                job_ids = list(JOB_POSTINGS.keys())
                job_markdown = view_jobs_markdown()
                
                # Returns updated job lists/dropdown for the student portal
                return (username, role), f"✅ Login Success! Welcome, {username} ({role.upper()}).", gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), gr.update(choices=job_ids), gr.update(value=job_markdown), gr.update(choices=job_ids)
            elif role == "hr":
                return (username, role), f"✅ Login Success! Welcome, {username} ({role.upper()}).", gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), gr.update(choices=[]), gr.update(value=""), gr.update(choices=[])
        else:
            return (None, "guest"), "❌ Login Failed: Invalid password.", gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), gr.update(choices=[]), gr.update(value=""), gr.update(choices=[])
    else:
        return (None, "guest"), "❌ Login Failed: Invalid username or password.", gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), gr.update(choices=[]), gr.update(value=""), gr.update(choices=[])

def user_logout():
    # Resetting job dropdowns for safety
    return (None, "guest"), "👋 Logged out. Please log in again.", gr.update(visible=False), gr.update(visible=False), gr.update(visible=True)


# --- CORE FUNCTIONALITY (RESUME GENERATION - UNCHANGED) ---
def generate_resume(name, email_id, contact_no, linkedin_url, objective, skills, education, experience, projects_input, certifications_input, prompt_extra):
    """Generates the AI text and the DOCX file with all fields from divya_resume.pdf."""
    
    if not name or not skills or not education:
        return "❌ Error: Please fill in Full Name, Key Skills, and Education to generate a resume.", "💡 No guidance available. Fill in required fields.", None
    
    safe_name = re.sub(r'[^a-zA-Z0-9_]', '', name.replace(' ', '_'))
    file_path = f"Professional_Resume_{safe_name}_{int(time.time())}.docx"

    prompt = f"""Generate a clean, professional resume text for:
Name: {name}
Skills: {skills}
Education: {education}
Experience: {experience}
{prompt_extra if prompt_extra else ""}
Ensure the structure includes Summary, Skills, Education, Experience, and Certifications.
"""

    try:
        # Model generation logic (Mock/Real)
        if isinstance(model, MockModel):
            outputs = model.generate(prompt, max_new_tokens=400, num_return_sequences=1)
            raw_text = tokenizer.decode(outputs, skip_special_tokens=True) 
        else:
            inputs = tokenizer(prompt, return_tensors="pt")["input_ids"]
            outputs = model.generate(inputs, max_length=600, num_return_sequences=1)
            raw_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

        resume_text = raw_text.replace(prompt, "").strip()
        resume_text = re.sub(r"<.*?>", "", resume_text).strip()
        if not resume_text:
            resume_text = generate_llm_output(prompt)
                
        # Create Word document
        doc = Document()
        doc.add_paragraph(name.upper()).alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.add_paragraph(f"Email id: {email_id} | Contact no: {contact_no} | LinkedIn: {linkedin_url}").alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        doc.add_heading("CAREER OBJECTIVE", level=1)
        doc.add_paragraph(objective if objective.strip() else "To leverage my skills...")
        
        doc.add_heading("EDUCATION", level=1)
        doc.add_paragraph(education)
        
        doc.add_heading("SKILLS", level=1)
        doc.add_paragraph(f"Programming Languages: {skills} \nFrontend Technologies: HTML5, CSS3, Bootstrap \nDatabase: SQL \nSoft Skills: Teamwork, Problem-solving.")
        
        doc.add_heading("INTERNSHIPS", level=1)
        doc.add_paragraph(experience if experience.lower().strip() not in ["none", ""] else "No formal internships or major experience listed.")
            
        doc.add_heading("PROJECTS", level=1)
        doc.add_paragraph(projects_input if projects_input.lower().strip() not in ["none", ""] else "• Default Project 1\n• Default Project 2")
        
        doc.add_heading("CERTIFICATIONS", level=1)
        doc.add_paragraph(certifications_input if certifications_input.lower().strip() not in ["none", ""] else "• Default Certification 1\n• Default Certification 2")

        doc.save(file_path)

        guidance = f"""
### 💡 Resume Enhancement Tips:
- **Tailor:** Did you mention skills specific to the job you are applying for?
- **Metrics:** Use numbers to quantify your achievements (e.g., *Reduced costs by 15%*).
- **File:** Your DOCX file, **{file_path}**, is ready for download.
"""
        
        return resume_text, guidance, file_path
    
    except Exception as e:
        error_msg = f"❌ Resume Generation Failed: An unexpected error occurred.\nError: {type(e).__name__}: {str(e)}"
        print(error_msg)
        return error_msg, f"💡 An error occurred during processing.", None


# --- HR JOB POSTING FUNCTIONS (MODIFIED to use more distinct ID) ---

def post_job(title, company, description):
    if not title or not company or not description:
        # Return updates for all relevant components
        return gr.update(value=title), gr.update(value=company), gr.update(value=description), view_jobs_markdown(), f"❌ Error: All job fields are required to post.", gr.update(choices=list(JOB_POSTINGS.keys()), value=None), gr.update(choices=list(JOB_POSTINGS.keys()), value=None)

    job_id = f"{company.upper()[:3]}-{random.randint(100, 999)}-{int(time.time()) % 1000}"
    JOB_POSTINGS[job_id] = {
        "title": title,
        "company": company,
        "description": description,
        "posted_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    job_keys = list(JOB_POSTINGS.keys())
    
    # Update job_dropdown and ats_job_dropdown
    return gr.update(value=""), gr.update(value=""), gr.update(value=""), view_jobs_markdown(), f"✅ Success! Job **'{title}'** posted with ID: **{job_id}**", gr.update(choices=job_keys), gr.update(choices=job_keys)

def view_jobs_markdown():
    if not JOB_POSTINGS:
        return "No job postings available at this time."
        
    job_list_markdown = "### Available Job Openings\n"
    for jid, job in JOB_POSTINGS.items():
        job_list_markdown += f"#### {job['title']} at {job['company']}\n"
        job_list_markdown += f"**ID:** `{jid}` | **Posted:** {job['posted_at']}\n"
        truncated_desc = job['description'][:150].replace('\n', ' ') + ("..." if len(job['description']) > 150 else "")
        job_list_markdown += f"{truncated_desc}\n\n"
    return job_list_markdown


# --- APPLICANT INTERACTION FUNCTIONS (SIMPLIFIED) ---

def select_job_details(job_id):
    """Returns the description markdown for a selected job for the main job listing view."""
    if job_id and job_id in JOB_POSTINGS:
        job = JOB_POSTINGS[job_id]
        details = (
            f"### {job['title']} at {job['company']}\n"
            f"**Job ID:** {job_id}\n"
            f"**Posted:** {job['posted_at']}\n\n"
            f"**Description:**\n{job['description']}"
        )
        return details
    return "Please select a job ID to view the full description."

def get_job_description_for_ats(job_id):
    """Returns the raw job description text for the ATS input box."""
    if job_id and job_id in JOB_POSTINGS:
        return JOB_POSTINGS[job_id]['description']
    return "Select a job ID to load the description."


# --- NEW: ATS SCORE CALCULATION FUNCTION ---

def calculate_ats_score(resume_text, job_id):
    if not job_id or job_id not in JOB_POSTINGS:
        return "❌ **Error**: Please select a valid Job ID first.", gr.update(value=get_job_description_for_ats(job_id))

    if not resume_text:
        return "❌ **Error**: Please paste your resume text to check the score.", gr.update(value=get_job_description_for_ats(job_id))

    job_description = JOB_POSTINGS[job_id]['description'].lower()
    resume_lower = resume_text.lower()
    
    # 1. Keyword Extraction (simplistic but effective mock)
    stop_words = set(['and', 'the', 'a', 'an', 'is', 'to', 'in', 'of', 'with', 'for', 'you', 'we', 'are', 'be', 'at', 'by', 'on', 'our', 'this', 'that', 'from', 'as', 'will', 'must', 'skills', 'experience', 'ability', 'work', 'data', 'using', 'job', 'role', 'team', 'etc', 'etc.'])
    
    # Extract keywords (>= 4 characters, not a stop word)
    job_keywords = set(re.findall(r'\b\w{4,}\b', job_description))
    job_keywords = {word for word in job_keywords if word not in stop_words}
    
    resume_keywords = set(re.findall(r'\b\w{4,}\b', resume_lower))
    
    # 2. Score Calculation
    matched_keywords = job_keywords.intersection(resume_keywords)
    
    total_job_keywords = len(job_keywords)
    matched_count = len(matched_keywords)
    
    if total_job_keywords == 0:
        return "⚠️ **ATS Error**: Job description is too generic for meaningful scoring.", gr.update(value=get_job_description_for_ats(job_id))

    # Match percentage, then adjust to a 100 point scale (max 95)
    match_percentage = (matched_count / total_job_keywords) * 100
    ats_score = min(95, int(match_percentage * 1.5 + 40)) 
    
    if ats_score < 40: ats_score = random.randint(30, 45) # Min score limit

    match_list = "\n- ".join(matched_keywords)
    
    output = f"## 🤖 ATS Match Score: **{ats_score}%**\n\n"
    
    if ats_score >= 80:
        output += "🎉 **Excellent Match!** Your resume is highly tailored to this job. Expect strong visibility."
    elif ats_score >= 60:
        output += "👍 **Good Match.** Your resume covers many key areas. Consider adding more keywords from the description."
    else:
        output += "⚠️ **Moderate Match.** Your resume is missing several key job keywords. Review the job description and tailor your skills and experience sections."
        
    output += f"\n\n---\n\n### Matched Keywords ({matched_count}/{total_job_keywords}):\n- {match_list if match_list else 'None matched.'}"
    
    return output, gr.update(value=get_job_description_for_ats(job_id))


# --- GRADIO INTERFACE SETUP ---

custom_css = """
.gradio-container { background: #f0f0f0; }
.textbox-bordered { border: 3px solid #1E3A8A; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.2); }
.custom-run-button { background-color: #0072CE !important; color: white !important; font-weight: bold; border-radius: 8px; padding: 10px 20px; }
.hr-header { color: #D61B1F; font-size: 1.5em; font-weight: bold; }
.applicant-header { color: #0072CE; font-size: 1.5em; font-weight: bold; }
.auth-title { color: #1E3A8A; font-size: 2em; }
"""

with gr.Blocks(css=custom_css) as demo:
    
    # --- State Variables ---
    auth_state = gr.State((None, "guest"))
    
    gr.Markdown("# 🏢 IBM Granite AI Career Portal")

    # 1. Define all Components
    with gr.Tabs() as main_tabs:
        
        # --- TAB 1: LOGIN / REGISTER (Unchanged) ---
        with gr.TabItem("Authentication", elem_id="auth_tab") as auth_tab:
            gr.Markdown("<div class='auth-title'>Access Portal</div>")
            login_status_msg = gr.Markdown("Please login or register to use the portals.")
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 📝 New User Registration")
                    reg_user = gr.Textbox(label="Username")
                    reg_pass = gr.Textbox(label="Password", type="password")
                    reg_role = gr.Radio(["student", "hr"], label="Account Type")
                    register_btn = gr.Button("Register Account", variant="secondary")
                    reg_message = gr.Markdown("")
                    
                with gr.Column(scale=1):
                    gr.Markdown("### 🔑 Existing User Login")
                    login_user = gr.Textbox(label="Username")
                    login_pass = gr.Textbox(label="Password", type="password")
                    login_btn = gr.Button("Login to Portal", variant="primary")
        
        # --- TAB 2: APPLICANT PORTAL (ATS Tab Added) ---
        with gr.TabItem("Applicant Portal", visible=False) as applicant_tab:
            
            gr.Markdown("<div class='applicant-header'>AI Resume Generation & Tools</div>")
            
            with gr.Tabs():
                
                # --- SUB-TAB 1: RESUME BUILDER ---
                with gr.TabItem("Resume Builder"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            gr.Markdown("### 👤 Personal Details & Resume Builder")
                            name = gr.Textbox(label="Full Name", value="Divya Tadisetti")
                            with gr.Row():
                                email_id = gr.Textbox(label="Email id", value="dtadisetti8@gmail.com")
                                contact_no = gr.Textbox(label="Contact no", value="9989059362")
                            linkedin_url = gr.Textbox(label="LinkedIn URL", value="divya-tadisetti-161336304")
                            gr.Markdown("---")
                            objective = gr.Textbox(label="Career Objective", lines=3, placeholder="To leverage my skills...", value="To leverage my skills in programming, data analysis, and problem-solving to contribute to innovative projects and achieve professional growth in a dynamic environment.")
                            skills = gr.Textbox(label="Key Skills (Programming/Tech)", value="C, Python, Java, HTML5, CSS3, Bootstrap, SQL")
                            education = gr.Textbox(label="Education", lines=2, value="Seshadri Rao Gudlavalleru Engineering College, BTech in Computer Science and Engineering | GPA: 9.20 | 2026")
                            gr.Markdown("---")
                            experience = gr.Textbox(label="Internships / Experience", lines=3, placeholder="List your internships and professional roles here.", value="Cyber security AIMER Society (July-2024): Learned threat detection and risk assessment; Generative Al with IBM Cloud- Smartinternz(July -2025): Built small-scale Al model deployment project")
                            projects_input = gr.Textbox(label="Projects", lines=3, placeholder="Separate projects with a new line or bullet points.", value="Loan Approval Analytics: A Classification-Based Data Mining Approach; Smart SDLC AI-Enhanced Software Development Life Cycle")
                            certifications_input = gr.Textbox(label="Certifications", lines=2, placeholder="List certifications separated by new lines.", value="Python Basics for Data Science - IBM; NPTEL certification in Social Networks")
                            gr.Markdown("---")
                            prompt_extra = gr.Textbox(label="Additional Instructions for AI", lines=1, placeholder="e.g., Focus on leadership skills for a managerial role.", value="NONE") 
                            run = gr.Button("✨ Generate Professional Resume", elem_classes=["custom-run-button"])
                        
                        with gr.Column(scale=2):
                            gr.Markdown("### Resume Output")
                            with gr.Tab("AI Generated Text"):
                                resume_out = gr.Textbox(label="📄 Review AI Generated Text (LLM Raw Output)", lines=10, elem_classes=["textbox-bordered"])
                            with gr.Tab("Guidance"):
                                guidance_out = gr.Markdown("💡 Guidance and Tips will appear here after generation.")
                            
                            download = gr.File(label="⬇️ Download Formatted .docx File")

                # --- SUB-TAB 2: JOB DETAILS & LISTING ---
                with gr.TabItem("Job Listings"):
                    gr.Markdown("### 📜 Job Listing Details")
                    with gr.Row():
                        with gr.Column(scale=1):
                            job_summary = gr.Markdown(view_jobs_markdown(), label="Job Summary List")
                            
                        with gr.Column(scale=2):
                            gr.Markdown("#### Select a Job ID to view the full description")
                            job_dropdown = gr.Dropdown(
                                choices=[], 
                                label="Select Job ID",
                                interactive=True
                            )
                            job_description_out = gr.Markdown("Select a job ID from the dropdown to view the description.")
                
                # --- SUB-TAB 3: ATS SCORE CHECK (NEW) ---
                with gr.TabItem("ATS Score Check"):
                    gr.Markdown("### 🎯 Resume ATS Match Checker")
                    gr.Markdown("Select a job and paste your generated resume text to see how well it matches the required keywords.")
                    
                    with gr.Row():
                        with gr.Column(scale=1):
                            ats_job_dropdown = gr.Dropdown(
                                choices=[], 
                                label="1. Select Target Job ID",
                                interactive=True
                            )
                            check_ats_btn = gr.Button("🔍 Check ATS Score", variant="primary")
                            
                            gr.Markdown("#### Job Description (Read-only)")
                            ats_job_desc_out = gr.Textbox(label="", lines=10, interactive=False, value="Select a job ID to load the description.")
                            
                        with gr.Column(scale=2):
                            ats_resume_text = gr.Textbox(
                                label="2. Paste Generated Resume Text Here (From Resume Builder tab)", 
                                lines=15, 
                                placeholder="Paste the text from the 'AI Generated Text' tab for accurate scoring.",
                                elem_classes=["textbox-bordered"]
                            )
                            ats_score_out = gr.Markdown("Score and keyword analysis will appear here.")


            logout_btn_applicant = gr.Button("Logout", variant="secondary")

        # --- TAB 3: HR PORTAL (Unchanged Structure) ---
        with gr.TabItem("HR Portal", visible=False) as hr_tab:
            
            gr.Markdown("<div class='hr-header'>HR Management Portal: Post New Job Applications</div>")
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 📋 Post New Job")
                    job_title = gr.Textbox(label="Job Title", placeholder="e.g., Senior Data Scientist")
                    job_company = gr.Textbox(label="Company Name", placeholder="e.g., IBM")
                    job_description = gr.Textbox(label="Job Description", lines=5, placeholder="Paste the full job description here.")
                    post_btn = gr.Button("Post Job", variant="primary")
                    posting_message = gr.Markdown("Job posting status will appear here.")
                    
                with gr.Column(scale=2):
                    gr.Markdown("### 📜 Current Active Job Postings")
                    current_jobs_out = gr.Markdown(view_jobs_markdown(), visible=True)

            logout_btn_hr = gr.Button("Logout", variant="secondary")
            
    
    # 2. Define all Event Handlers (Click functions)

    # --- Registration Logic (Unchanged) ---
    register_btn.click(
        register_user,
        inputs=[reg_user, reg_pass, reg_role],
        outputs=[reg_message, reg_user, reg_pass, reg_role, login_user, login_pass]
    )
    
    # --- Login Logic (Updates both job_dropdowns for Applicant Portal) ---
    login_btn.click(
        user_login,
        inputs=[login_user, login_pass],
        outputs=[auth_state, login_status_msg, applicant_tab, hr_tab, auth_tab, job_dropdown, job_summary, ats_job_dropdown]
    )

    # --- Applicant Resume Generation Logic (Unchanged) ---
    run.click(
        generate_resume,
        inputs=[
            name, email_id, contact_no, linkedin_url, objective, skills, 
            education, experience, projects_input, certifications_input, prompt_extra
        ],
        outputs=[resume_out, guidance_out, download] 
    )
    
    # --- Job Listing Interaction Logic (Unchanged) ---
    job_dropdown.change(
        select_job_details,
        inputs=[job_dropdown],
        outputs=[job_description_out]
    )
    
    # --- ATS Interaction Logic (NEW) ---
    ats_job_dropdown.change(
        get_job_description_for_ats,
        inputs=[ats_job_dropdown],
        outputs=[ats_job_desc_out]
    )
    
    check_ats_btn.click(
        calculate_ats_score,
        inputs=[ats_resume_text, ats_job_dropdown],
        outputs=[ats_score_out, ats_job_desc_out] # Update score and ensure description is shown
    )
    
    # --- HR Post Job Logic (Updates HR components and BOTH applicant dropdowns) ---
    post_btn.click(
        post_job,
        inputs=[job_title, job_company, job_description],
        # Outputs: job_title, job_company, job_description, current_jobs_out, posting_message, job_dropdown, ats_job_dropdown
        outputs=[job_title, job_company, job_description, current_jobs_out, posting_message, job_dropdown, ats_job_dropdown]
    ).then(
        view_jobs_markdown, 
        inputs=[],
        # Update Applicant Summary list
        outputs=[job_summary] 
    )
    
    # --- LOGOUT Logic (Shared) ---
    logout_btn_applicant.click(
        user_logout,
        inputs=[],
        outputs=[auth_state, login_status_msg, applicant_tab, hr_tab, auth_tab]
    )
    
    logout_btn_hr.click(
        user_logout,
        inputs=[],
        outputs=[auth_state, login_status_msg, applicant_tab, hr_tab, auth_tab]
    )

demo.launch()'''

# pip install gradio transformers python-docx
'''
import gradio as gr
from transformers import AutoTokenizer, AutoModelForCausalLM
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import re
import os
import time
import random 

# --- MOCK DATABASE AND STATE ---
USER_DB = {
    "test_hr": {"password": "hr_password", "role": "hr"},
    "test_student": {"password": "student_password", "role": "student"}
}
JOB_POSTINGS = {} 

# --- MOCK IMPLEMENTATION DEFINITION ---
def generate_llm_output(prompt):
    """Generates a structured mock AI response."""
    name_match = re.search(r"Name: (.*)", prompt)
    skills_match = re.search(r"Skills: (.*)", prompt)
    name = name_match.group(1).strip() if name_match else "Applicant Name"
    skills = skills_match.group(1).strip() if skills_match else "Python, Leadership, SQL"
    
    return f"***DUMMY AI RESPONSE***\n\n**SUMMARY:** Highly motivated individual ({name}) with a strong foundation in {skills}. Proven ability to tackle complex challenges and drive results.\n\n**SKILLS:** {skills}\n\n**EXPERIENCE:** Simulated job experience here, demonstrating proficiency in key skills.\n\n**EDUCATION:** University details here."

class MockModel:
    def generate(self, input_ids, max_new_tokens, num_return_sequences):
        return {"input_ids": input_ids} 

class MockTokenizer:
    def __init__(self): self.eos_token = ""
    def __call__(self, text, *args, **kwargs): return {"input_ids": text}
    def decode(self, tokens, skip_special_tokens=True): 
        if isinstance(tokens, dict) and "input_ids" in tokens:
            tokens = tokens["input_ids"]
        if isinstance(tokens, str):
            return generate_llm_output(tokens)
        return generate_llm_output("Default Name: Default, Skills: Default")


# --- IBM Granite Model Loading (MOCK FALLBACK) ---

tokenizer = None
model = None

try:
    # Attempt to load the real model, falling back to mock if failed
    tokenizer = AutoTokenizer.from_pretrained("ibm-granite/granite-3.3-2b-instruct")
    model = AutoModelForCausalLM.from_pretrained("ibm-granite/granite-3.3-2b-instruct")
    print("SUCCESS: Loaded IBM Granite model.")
except Exception as e:
    print(f"Warning: Could not load Granite model. Using DUMMY/MOCK function. Error: {e}")
    model = MockModel()
    tokenizer = MockTokenizer()


# --- AUTHENTICATION FUNCTIONS (UNCHANGED) ---

def register_user(username, password, role):
    if not username or not password or not role:
        return "❌ Registration failed: All fields are required.", gr.update(value=""), gr.update(value=""), gr.update(value=None), gr.update(value=""), gr.update(value="")
               
    username = username.strip()
    password = password.strip()
    
    if username in USER_DB:
        return f"❌ Registration failed: User '{username}' already exists.", gr.update(value=""), gr.update(value=""), gr.update(value=None), gr.update(value=""), gr.update(value="")
    
    USER_DB[username] = {"password": password, "role": role}
    
    return f"✅ Success! User '{username}' registered as **{role.upper()}**. Please proceed to the Login section.", gr.update(value=""), gr.update(value=""), gr.update(value=None), gr.update(value=""), gr.update(value="")


def user_login(username, password):
    username = username.strip()
    password = password.strip()
    
    if username in USER_DB:
        if USER_DB[username]["password"] == password:
            role = USER_DB[username]["role"]
            
            if role == "student":
                job_ids = list(JOB_POSTINGS.keys())
                job_markdown = view_jobs_markdown()
                
                # Returns updated job lists/dropdown for the student portal
                return (username, role), f"✅ Login Success! Welcome, {username} ({role.upper()}).", gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), gr.update(choices=job_ids), gr.update(value=job_markdown), gr.update(choices=job_ids)
            elif role == "hr":
                return (username, role), f"✅ Login Success! Welcome, {username} ({role.upper()}).", gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), gr.update(choices=[]), gr.update(value=""), gr.update(choices=[])
        else:
            return (None, "guest"), "❌ Login Failed: Invalid password.", gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), gr.update(choices=[]), gr.update(value=""), gr.update(choices=[])
    else:
        return (None, "guest"), "❌ Login Failed: Invalid username or password.", gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), gr.update(choices=[]), gr.update(value=""), gr.update(choices=[])

def user_logout():
    # Resetting job dropdowns for safety
    return (None, "guest"), "👋 Logged out. Please log in again.", gr.update(visible=False), gr.update(visible=False), gr.update(visible=True)


# --- CORE FUNCTIONALITY (RESUME GENERATION - UNCHANGED) ---
def generate_resume(name, email_id, contact_no, linkedin_url, objective, skills, education, experience, projects_input, certifications_input, prompt_extra):
    """Generates the AI text and the DOCX file with all fields from divya_resume.pdf."""
    
    if not name or not skills or not education:
        return "❌ Error: Please fill in Full Name, Key Skills, and Education to generate a resume.", "💡 No guidance available. Fill in required fields.", None
    
    safe_name = re.sub(r'[^a-zA-Z0-9_]', '', name.replace(' ', '_'))
    file_path = f"Professional_Resume_{safe_name}_{int(time.time())}.docx"

    prompt = f"""Generate a clean, professional resume text for:
Name: {name}
Skills: {skills}
Education: {education}
Experience: {experience}
{prompt_extra if prompt_extra else ""}
Ensure the structure includes Summary, Skills, Education, Experience, and Certifications.
"""

    try:
        # Model generation logic (Mock/Real)
        if isinstance(model, MockModel):
            outputs = model.generate(prompt, max_new_tokens=400, num_return_sequences=1)
            raw_text = tokenizer.decode(outputs, skip_special_tokens=True) 
        else:
            inputs = tokenizer(prompt, return_tensors="pt")["input_ids"]
            outputs = model.generate(inputs, max_length=600, num_return_sequences=1)
            raw_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

        resume_text = raw_text.replace(prompt, "").strip()
        resume_text = re.sub(r"<.*?>", "", resume_text).strip()
        if not resume_text:
            resume_text = generate_llm_output(prompt)
                
        # Create Word document
        doc = Document()
        doc.add_paragraph(name.upper()).alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.add_paragraph(f"Email id: {email_id} | Contact no: {contact_no} | LinkedIn: {linkedin_url}").alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        doc.add_heading("CAREER OBJECTIVE", level=1)
        doc.add_paragraph(objective if objective.strip() else "To leverage my skills...")
        
        doc.add_heading("EDUCATION", level=1)
        doc.add_paragraph(education)
        
        doc.add_heading("SKILLS", level=1)
        doc.add_paragraph(f"Programming Languages: {skills} \nFrontend Technologies: HTML5, CSS3, Bootstrap \nDatabase: SQL \nSoft Skills: Teamwork, Problem-solving.")
        
        doc.add_heading("INTERNSHIPS", level=1)
        doc.add_paragraph(experience if experience.lower().strip() not in ["none", ""] else "No formal internships or major experience listed.")
            
        doc.add_heading("PROJECTS", level=1)
        doc.add_paragraph(projects_input if projects_input.lower().strip() not in ["none", ""] else "• Default Project 1\n• Default Project 2")
        
        doc.add_heading("CERTIFICATIONS", level=1)
        doc.add_paragraph(certifications_input if certifications_input.lower().strip() not in ["none", ""] else "• Default Certification 1\n• Default Certification 2")

        doc.save(file_path)

        guidance = f"""
### 💡 Resume Enhancement Tips:
- **Tailor:** Did you mention skills specific to the job you are applying for?
- **Metrics:** Use numbers to quantify your achievements (e.g., *Reduced costs by 15%*).
- **File:** Your DOCX file, **{file_path}**, is ready for download.
"""
        
        return resume_text, guidance, file_path
    
    except Exception as e:
        error_msg = f"❌ Resume Generation Failed: An unexpected error occurred.\nError: {type(e).__name__}: {str(e)}"
        print(error_msg)
        return error_msg, f"💡 An error occurred during processing.", None


# --- HR JOB POSTING FUNCTIONS (MODIFIED to use more distinct ID) ---

def post_job(title, company, description):
    if not title or not company or not description:
        # Return updates for all relevant components
        return gr.update(value=title), gr.update(value=company), gr.update(value=description), view_jobs_markdown(), f"❌ Error: All job fields are required to post.", gr.update(choices=list(JOB_POSTINGS.keys()), value=None), gr.update(choices=list(JOB_POSTINGS.keys()), value=None)

    job_id = f"{company.upper()[:3]}-{random.randint(100, 999)}-{int(time.time()) % 1000}"
    JOB_POSTINGS[job_id] = {
        "title": title,
        "company": company,
        "description": description,
        "posted_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    job_keys = list(JOB_POSTINGS.keys())
    
    # Update job_dropdown and ats_job_dropdown
    return gr.update(value=""), gr.update(value=""), gr.update(value=""), view_jobs_markdown(), f"✅ Success! Job **'{title}'** posted with ID: **{job_id}**", gr.update(choices=job_keys), gr.update(choices=job_keys)

def view_jobs_markdown():
    if not JOB_POSTINGS:
        return "No job postings available at this time."
        
    job_list_markdown = "### Available Job Openings\n"
    for jid, job in JOB_POSTINGS.items():
        job_list_markdown += f"#### {job['title']} at {job['company']}\n"
        job_list_markdown += f"**ID:** `{jid}` | **Posted:** {job['posted_at']}\n"
        truncated_desc = job['description'][:150].replace('\n', ' ') + ("..." if len(job['description']) > 150 else "")
        job_list_markdown += f"{truncated_desc}\n\n"
    return job_list_markdown


# --- APPLICANT INTERACTION FUNCTIONS (SIMPLIFIED) ---

def select_job_details(job_id):
    """Returns the description markdown for a selected job for the main job listing view."""
    if job_id and job_id in JOB_POSTINGS:
        job = JOB_POSTINGS[job_id]
        details = (
            f"### {job['title']} at {job['company']}\n"
            f"**Job ID:** {job_id}\n"
            f"**Posted:** {job['posted_at']}\n\n"
            f"**Description:**\n{job['description']}"
        )
        return details
    return "Please select a job ID to view the full description."

def get_job_description_for_ats(job_id):
    """Returns the raw job description text for the ATS input box."""
    if job_id and job_id in JOB_POSTINGS:
        return JOB_POSTINGS[job_id]['description']
    return "Select a job ID to load the description."

# --- NEW HELPER: File Text Extraction ---

def extract_text_from_file(file_path):
    """Extracts text content from uploaded files, currently supporting DOCX."""
    if not file_path:
        return None, "❌ Error: No file uploaded."
    
    file_extension = os.path.splitext(file_path)[1].lower()
    
    if file_extension == '.docx':
        try:
            document = Document(file_path)
            text = '\n'.join([paragraph.text for paragraph in document.paragraphs])
            return text, "✅ Text successfully extracted from DOCX file."
        except Exception as e:
            return None, f"❌ Error reading DOCX file: {e}"
            
    elif file_extension == '.pdf':
        # NOTE: PDF requires 'pypdf' or 'pdfminer.six' which may not be available. 
        # For simplicity in this environment, we issue a warning.
        return None, "⚠️ **PDF Files are not fully supported** in this environment due to missing dependencies. Please use a **.docx** file for accurate scoring."
        
    else:
        return None, f"⚠️ Unsupported file type: **{file_extension}**. Please upload a **.docx** file."


# --- NEW: ATS SCORE CALCULATION FUNCTION (MODIFIED) ---

def calculate_ats_score(ats_resume_file, job_id):
    """
    Calculates the ATS match score based on keyword overlap between 
    the uploaded resume file and the selected job description.
    """
    if not job_id or job_id not in JOB_POSTINGS:
        return "❌ **Error**: Please select a valid Job ID first.", gr.update(value=get_job_description_for_ats(job_id))

    # 1. Extract Resume Text
    resume_text, status_msg = extract_text_from_file(ats_resume_file.name if ats_resume_file else None)

    if not resume_text:
        return f"❌ **Error**: {status_msg}", gr.update(value=get_job_description_for_ats(job_id))

    job_description = JOB_POSTINGS[job_id]['description'].lower()
    resume_lower = resume_text.lower()
    
    # 2. Keyword Extraction 
    stop_words = set(['and', 'the', 'a', 'an', 'is', 'to', 'in', 'of', 'with', 'for', 'you', 'we', 'are', 'be', 'at', 'by', 'on', 'our', 'this', 'that', 'from', 'as', 'will', 'must', 'skills', 'experience', 'ability', 'work', 'data', 'using', 'job', 'role', 'team', 'etc', 'etc.', 'responsibilities', 'duties', 'project', 'develop', 'using', 'years', 'required', 'strong', 'knowledge', 'demonstrated', 'related', 'bachelor', 'degree'])
    
    # Extract keywords (>= 4 characters, not a stop word)
    job_keywords = set(re.findall(r'\b\w{4,}\b', job_description))
    job_keywords = {word for word in job_keywords if word not in stop_words and not word.isdigit()}
    
    resume_keywords = set(re.findall(r'\b\w{4,}\b', resume_lower))
    
    # 3. Score Calculation
    matched_keywords = job_keywords.intersection(resume_keywords)
    unmatched_keywords = job_keywords.difference(resume_keywords)
    
    total_job_keywords = len(job_keywords)
    matched_count = len(matched_keywords)
    
    if total_job_keywords == 0:
        return "⚠️ **ATS Error**: Job description is too generic for meaningful scoring.", gr.update(value=get_job_description_for_ats(job_id))

    match_percentage = (matched_count / total_job_keywords) * 100
    ats_score = min(95, int(match_percentage * 1.5 + 40)) 
    
    if ats_score < 40: ats_score = random.randint(30, 45) # Min score limit

    match_list = "\n- ".join(matched_keywords)
    unmatch_list = "\n- ".join(unmatched_keywords)
    
    output = f"## 🤖 ATS Match Score: **{ats_score}%**\n\n"
    output += f"*{status_msg}*\n\n" # Display file status

    # Generate Improvement Tips
    tips = "\n\n---\n\n### 📝 Resume Improvement Tips:\n"
    if ats_score >= 80:
        output += "🎉 **Excellent Match!** Your resume is highly tailored to this job. Expect strong visibility."
        tips += "- **Minor Tweaks:** Only minor formatting checks are needed. You're ready to apply!"
    elif ats_score >= 60:
        output += "👍 **Good Match.** Your resume covers many key areas. Action is recommended."
        tips += "- **Targeted Addition:** Explicitly include the **Unmatched Keywords** in your experience or skills sections.\n"
        tips += "- **Quantify Results:** Ensure your bullet points use numbers (e.g., 'increased efficiency by 20%')."
    else:
        output += "⚠️ **Moderate Match.** Your resume is missing several key job keywords. **Immediate action is required.**"
        tips += "- **Critical Missing Keywords:** The system did not find these important keywords: \n> " + (unmatch_list if unmatch_list else "*(None listed, check other sections)*") + "\n"
        tips += "- **Restructure:** Use the exact terminology from the job description in your resume to maximize your match score."
        tips += "- **Format Check:** Ensure your resume is clean and uses standard section headings (Education, Experience, Skills)."
        
    output += tips
    output += f"\n\n---\n\n### Matched Keywords ({matched_count}/{total_job_keywords}):\n- {match_list if match_list else 'None matched.'}"
    
    return output, gr.update(value=get_job_description_for_ats(job_id))


# --- GRADIO INTERFACE SETUP ---

custom_css = """
.gradio-container { background: #f0f0f0; }
.textbox-bordered { border: 3px solid #1E3A8A; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.2); }
.custom-run-button { background-color: #0072CE !important; color: white !important; font-weight: bold; border-radius: 8px; padding: 10px 20px; }
.hr-header { color: #D61B1F; font-size: 1.5em; font-weight: bold; }
.applicant-header { color: #0072CE; font-size: 1.5em; font-weight: bold; }
.auth-title { color: #1E3A8A; font-size: 2em; }
"""

with gr.Blocks(css=custom_css) as demo:
    
    # --- State Variables ---
    auth_state = gr.State((None, "guest"))
    
    gr.Markdown("# 🏢 IBM Granite AI Career Portal")

    # 1. Define all Components
    with gr.Tabs() as main_tabs:
        
        # --- TAB 1: LOGIN / REGISTER (Unchanged) ---
        with gr.TabItem("Authentication", elem_id="auth_tab") as auth_tab:
            gr.Markdown("<div class='auth-title'>Access Portal</div>")
            login_status_msg = gr.Markdown("Please login or register to use the portals.")
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 📝 New User Registration")
                    reg_user = gr.Textbox(label="Username")
                    reg_pass = gr.Textbox(label="Password", type="password")
                    reg_role = gr.Radio(["student", "hr"], label="Account Type")
                    register_btn = gr.Button("Register Account", variant="secondary")
                    reg_message = gr.Markdown("")
                    
                with gr.Column(scale=1):
                    gr.Markdown("### 🔑 Existing User Login")
                    login_user = gr.Textbox(label="Username")
                    login_pass = gr.Textbox(label="Password", type="password")
                    login_btn = gr.Button("Login to Portal", variant="primary")
        
        # --- TAB 2: APPLICANT PORTAL (ATS Tab Modified) ---
        with gr.TabItem("Applicant Portal", visible=False) as applicant_tab:
            
            gr.Markdown("<div class='applicant-header'>AI Resume Generation & Tools</div>")
            
            with gr.Tabs():
                
                # --- SUB-TAB 1: RESUME BUILDER ---
                with gr.TabItem("Resume Builder"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            gr.Markdown("### 👤 Personal Details & Resume Builder")
                            name = gr.Textbox(label="Full Name")
                            with gr.Row():
                                email_id = gr.Textbox(label="Email id")
                                contact_no = gr.Textbox(label="Contact no")
                            linkedin_url = gr.Textbox(label="LinkedIn URL")
                            gr.Markdown("---")
                            objective = gr.Textbox(label="Career Objective", lines=3, placeholder="To leverage my skills...")
                            skills = gr.Textbox(label="Key Skills (Programming/Tech)")
                            education = gr.Textbox(label="Education", lines=2)
                            gr.Markdown("---")
                            experience = gr.Textbox(label="Internships / Experience", lines=3, placeholder="List your internships and professional roles here.")
                            projects_input = gr.Textbox(label="Projects", lines=3, placeholder="Separate projects with a new line or bullet points.")
                            certifications_input = gr.Textbox(label="Certifications", lines=2, placeholder="List certifications separated by new lines.")
                            gr.Markdown("---")
                            prompt_extra = gr.Textbox(label="Additional Instructions for AI", lines=1, placeholder="e.g., Focus on leadership skills for a managerial role.") 
                            run = gr.Button("✨ Generate Professional Resume", elem_classes=["custom-run-button"])
                        
                        with gr.Column(scale=2):
                            gr.Markdown("### Resume Output")
                            with gr.Tab("AI Generated Text"):
                                resume_out = gr.Textbox(label="📄 Review AI Generated Text (LLM Raw Output)", lines=10, elem_classes=["textbox-bordered"])
                            with gr.Tab("Guidance"):
                                guidance_out = gr.Markdown("💡 Guidance and Tips will appear here after generation.")
                            
                            download = gr.File(label="⬇️ Download Formatted .docx File")

                # --- SUB-TAB 2: JOB DETAILS & LISTING ---
                with gr.TabItem("Job Listings"):
                    gr.Markdown("### 📜 Job Listing Details")
                    with gr.Row():
                        with gr.Column(scale=1):
                            job_summary = gr.Markdown(view_jobs_markdown(), label="Job Summary List")
                            
                        with gr.Column(scale=2):
                            gr.Markdown("#### Select a Job ID to view the full description")
                            job_dropdown = gr.Dropdown(
                                choices=[], 
                                label="Select Job ID",
                                interactive=True
                            )
                            job_description_out = gr.Markdown("Select a job ID from the dropdown to view the description.")
                
                # --- SUB-TAB 3: ATS SCORE CHECK (NEW) ---
                with gr.TabItem("ATS Score Check"):
                    gr.Markdown("### 🎯 Resume ATS Match Checker")
                    gr.Markdown("Select a job and upload your resume file (**.docx** recommended) to see how well it matches the required keywords.")
                    
                    with gr.Row():
                        with gr.Column(scale=1):
                            ats_job_dropdown = gr.Dropdown(
                                choices=[], 
                                label="1. Select Target Job ID",
                                interactive=True
                            )
                            check_ats_btn = gr.Button("🔍 Calculate ATS Score & Tips", variant="primary")
                            
                            gr.Markdown("#### Job Description (Read-only)")
                            ats_job_desc_out = gr.Textbox(label="", lines=10, interactive=False, value="Select a job ID to load the description.")
                            
                        with gr.Column(scale=2):
                            # MODIFIED: Changed Textbox to File Upload component
                            ats_resume_file = gr.File(
                                label="2. Upload Resume File (.docx or .pdf)", 
                                type="filepath",
                                file_types=[".docx", ".pdf"]
                            )
                            ats_score_out = gr.Markdown("Score and detailed improvement tips will appear here.")


            logout_btn_applicant = gr.Button("Logout", variant="secondary")

        # --- TAB 3: HR PORTAL (Unchanged Structure) ---
        with gr.TabItem("HR Portal", visible=False) as hr_tab:
            
            gr.Markdown("<div class='hr-header'>HR Management Portal: Post New Job Applications</div>")
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 📋 Post New Job")
                    job_title = gr.Textbox(label="Job Title", placeholder="e.g., Senior Data Scientist")
                    job_company = gr.Textbox(label="Company Name", placeholder="e.g., IBM")
                    job_description = gr.Textbox(label="Job Description", lines=5, placeholder="Paste the full job description here.")
                    post_btn = gr.Button("Post Job", variant="primary")
                    posting_message = gr.Markdown("Job posting status will appear here.")
                    
                with gr.Column(scale=2):
                    gr.Markdown("### 📜 Current Active Job Postings")
                    current_jobs_out = gr.Markdown(view_jobs_markdown(), visible=True)

            logout_btn_hr = gr.Button("Logout", variant="secondary")
            
    
    # 2. Define all Event Handlers (Click functions)

    # --- Registration Logic (Unchanged) ---
    register_btn.click(
        register_user,
        inputs=[reg_user, reg_pass, reg_role],
        outputs=[reg_message, reg_user, reg_pass, reg_role, login_user, login_pass]
    )
    
    # --- Login Logic (Updates both job_dropdowns for Applicant Portal) ---
    login_btn.click(
        user_login,
        inputs=[login_user, login_pass],
        outputs=[auth_state, login_status_msg, applicant_tab, hr_tab, auth_tab, job_dropdown, job_summary, ats_job_dropdown]
    )

    # --- Applicant Resume Generation Logic (Unchanged) ---
    run.click(
        generate_resume,
        inputs=[
            name, email_id, contact_no, linkedin_url, objective, skills, 
            education, experience, projects_input, certifications_input, prompt_extra
        ],
        outputs=[resume_out, guidance_out, download] 
    )
    
    # --- Job Listing Interaction Logic (Unchanged) ---
    job_dropdown.change(
        select_job_details,
        inputs=[job_dropdown],
        outputs=[job_description_out]
    )
    
    # --- ATS Interaction Logic (MODIFIED to use file upload) ---
    ats_job_dropdown.change(
        get_job_description_for_ats,
        inputs=[ats_job_dropdown],
        outputs=[ats_job_desc_out]
    )
    
    check_ats_btn.click(
        calculate_ats_score,
        inputs=[ats_resume_file, ats_job_dropdown], # Input is the uploaded file
        outputs=[ats_score_out, ats_job_desc_out] 
    )
    
    # --- HR Post Job Logic (Updates HR components and BOTH applicant dropdowns) ---
    post_btn.click(
        post_job,
        inputs=[job_title, job_company, job_description],
        # Outputs: job_title, job_company, job_description, current_jobs_out, posting_message, job_dropdown, ats_job_dropdown
        outputs=[job_title, job_company, job_description, current_jobs_out, posting_message, job_dropdown, ats_job_dropdown]
    ).then(
        view_jobs_markdown, 
        inputs=[],
        # Update Applicant Summary list
        outputs=[job_summary] 
    )
    
    # --- LOGOUT Logic (Shared) ---
    logout_btn_applicant.click(
        user_logout,
        inputs=[],
        outputs=[auth_state, login_status_msg, applicant_tab, hr_tab, auth_tab]
    )
    
    logout_btn_hr.click(
        user_logout,
        inputs=[],
        outputs=[auth_state, login_status_msg, applicant_tab, hr_tab, auth_tab]
    )

demo.launch()'''

import gradio as gr
from transformers import AutoTokenizer, AutoModelForCausalLM
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import re
import os
import time
import random
import io # Added for file reading

# --- MOCK DATABASE AND STATE ---
USER_DB = {
    "test_hr": {"password": "hr_password", "role": "hr"},
    "test_student": {"password": "student_password", "role": "student"}
}
JOB_POSTINGS = {} 

# --- MOCK IMPLEMENTATION DEFINITION ---
def generate_llm_output(prompt):
    """Generates a structured mock AI response."""
    name_match = re.search(r"Name: (.*)", prompt)
    skills_match = re.search(r"Skills: (.*)", prompt)
    name = name_match.group(1).strip() if name_match else "Applicant Name"
    skills = skills_match.group(1).strip() if skills_match else "Python, Leadership, SQL"
    
    return f"***DUMMY AI RESPONSE***\n\n**SUMMARY:** Highly motivated individual ({name}) with a strong foundation in {skills}. Proven ability to tackle complex challenges and drive results.\n\n**SKILLS:** {skills}\n\n**EXPERIENCE:** Simulated job experience here, demonstrating proficiency in key skills.\n\n**EDUCATION:** University details here."

class MockModel:
    def generate(self, input_ids, max_new_tokens, num_return_sequences):
        return {"input_ids": input_ids} 

class MockTokenizer:
    def __init__(self): self.eos_token = ""
    def __call__(self, text, *args, **kwargs): return {"input_ids": text}
    def decode(self, tokens, skip_special_tokens=True): 
        if isinstance(tokens, dict) and "input_ids" in tokens:
            tokens = tokens["input_ids"]
        if isinstance(tokens, str):
            return generate_llm_output(tokens)
        return generate_llm_output("Default Name: Default, Skills: Default")


# --- IBM Granite Model Loading (MOCK FALLBACK) ---

tokenizer = None
model = None

try:
    # Attempting to load real model is kept for context, but will likely fail and use mock
    # tokenizer = AutoTokenizer.from_pretrained("ibm-granite/granite-3.3-2b-instruct")
    # model = AutoModelForCausalLM.from_pretrained("ibm-granite/granite-3.3-2b-instruct")
    # print("SUCCESS: Loaded IBM Granite model.")
    raise Exception("Simulated failure to ensure mock is used")
except Exception as e:
    # print(f"Warning: Could not load Granite model. Using DUMMY/MOCK function. Error: {e}")
    model = MockModel()
    tokenizer = MockTokenizer()


# --- AUTHENTICATION FUNCTIONS (UNCHANGED) ---

def register_user(username, password, role):
    if not username or not password or not role:
        return "❌ Registration failed: All fields are required.", gr.update(value=""), gr.update(value=""), gr.update(value=None), gr.update(value=""), gr.update(value="")
        
    username = username.strip()
    password = password.strip()
    
    if username in USER_DB:
        return f"❌ Registration failed: User '{username}' already exists.", gr.update(value=""), gr.update(value=""), gr.update(value=None), gr.update(value=""), gr.update(value="")
    
    USER_DB[username] = {"password": password, "role": role}
    
    return f"✅ Success! User '{username}' registered as **{role.upper()}**. Please proceed to the Login section.", gr.update(value=""), gr.update(value=""), gr.update(value=None), gr.update(value=""), gr.update(value="")


def user_login(username, password):
    username = username.strip()
    password = password.strip()
    
    if username in USER_DB:
        if USER_DB[username]["password"] == password:
            role = USER_DB[username]["role"]
            
            if role == "student":
                job_ids = list(JOB_POSTINGS.keys())
                job_markdown = view_jobs_markdown()
                
                # Returns updated job lists/dropdown for the student portal
                return (username, role), f"✅ Login Success! Welcome, {username} ({role.upper()}).", gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), gr.update(choices=job_ids), gr.update(value=job_markdown), gr.update(choices=job_ids)
            elif role == "hr":
                return (username, role), f"✅ Login Success! Welcome, {username} ({role.upper()}).", gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), gr.update(choices=[]), gr.update(value=""), gr.update(choices=[])
        else:
            return (None, "guest"), "❌ Login Failed: Invalid password.", gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), gr.update(choices=[]), gr.update(value=""), gr.update(choices=[])
    else:
        return (None, "guest"), "❌ Login Failed: Invalid username or password.", gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), gr.update(choices=[]), gr.update(value=""), gr.update(choices=[])

def user_logout():
    # Resetting job dropdowns for safety
    return (None, "guest"), "👋 Logged out. Please log in again.", gr.update(visible=False), gr.update(visible=False), gr.update(visible=True)


# --- CORE FUNCTIONALITY (RESUME GENERATION - UNCHANGED) ---
def generate_resume(name, email_id, contact_no, linkedin_url, objective, skills, education, experience, projects_input, certifications_input, prompt_extra):
    """Generates the AI text and the DOCX file with all fields from divya_resume.pdf."""
    
    if not name or not skills or not education:
        return "❌ Error: Please fill in Full Name, Key Skills, and Education to generate a resume.", "💡 No guidance available. Fill in required fields.", None
    
    safe_name = re.sub(r'[^a-zA-Z0-9_]', '', name.replace(' ', '_'))
    file_path = f"Professional_Resume_{safe_name}_{int(time.time())}.docx"

    prompt = f"""Generate a clean, professional resume text for:
Name: {name}
Skills: {skills}
Education: {education}
Experience: {experience}
{prompt_extra if prompt_extra else ""}
Ensure the structure includes Summary, Skills, Education, Experience, and Certifications.
"""

    try:
        # Model generation logic (Mock/Real)
        if isinstance(model, MockModel):
            outputs = model.generate(prompt, max_new_tokens=400, num_return_sequences=1)
            raw_text = tokenizer.decode(outputs, skip_special_tokens=True) 
        else:
            inputs = tokenizer(prompt, return_tensors="pt")["input_ids"]
            outputs = model.generate(inputs, max_length=600, num_return_sequences=1)
            raw_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

        resume_text = raw_text.replace(prompt, "").strip()
        resume_text = re.sub(r"<.*?>", "", resume_text).strip()
        if not resume_text:
            resume_text = generate_llm_output(prompt)
                
        # Create Word document
        doc = Document()
        doc.add_paragraph(name.upper()).alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.add_paragraph(f"Email id: {email_id} | Contact no: {contact_no} | LinkedIn: {linkedin_url}").alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        doc.add_heading("CAREER OBJECTIVE", level=1)
        doc.add_paragraph(objective if objective.strip() else "To leverage my skills...")
        
        doc.add_heading("EDUCATION", level=1)
        doc.add_paragraph(education)
        
        doc.add_heading("SKILLS", level=1)
        doc.add_paragraph(f"Programming Languages: {skills} \nFrontend Technologies: HTML5, CSS3, Bootstrap \nDatabase: SQL \nSoft Skills: Teamwork, Problem-solving.")
        
        doc.add_heading("INTERNSHIPS", level=1)
        doc.add_paragraph(experience if experience.lower().strip() not in ["none", ""] else "No formal internships or major experience listed.")
            
        doc.add_heading("PROJECTS", level=1)
        doc.add_paragraph(projects_input if projects_input.lower().strip() not in ["none", ""] else "• Default Project 1\n• Default Project 2")
        
        doc.add_heading("CERTIFICATIONS", level=1)
        doc.add_paragraph(certifications_input if certifications_input.lower().strip() not in ["none", ""] else "• Default Certification 1\n• Default Certification 2")

        doc.save(file_path)

        # Added tip generation for specific missing fields if applicable (Mock)
        missing_info = []
        if not experience or experience.lower().strip() in ["none", ""]:
             missing_info.append("- **Experience/Internships:** Your current resume lacks formal experience. Highlight relevant course projects or volunteer work to fill this gap.")
        if not projects_input or projects_input.lower().strip() in ["none", ""]:
            missing_info.append("- **Projects:** Add detailed projects with technologies used and quantifiable outcomes to showcase your practical skills.")
        
        guidance_text = f"""
### 💡 Resume Enhancement Tips:
- **Tailor:** Did you mention skills specific to the job you are applying for? Use the ATS checker!
- **Metrics:** Use numbers to quantify your achievements (e.g., *Reduced costs by 15%*).
{'\n'.join(missing_info) if missing_info else "- **General:** Looks good! Proceed to the ATS Checker to optimize for a specific job."}
- **File:** Your DOCX file, **{file_path}**, is ready for download.
"""
        
        return resume_text, guidance_text, file_path
    
    except Exception as e:
        error_msg = f"❌ Resume Generation Failed: An unexpected error occurred.\nError: {type(e).__name__}: {str(e)}"
        print(error_msg)
        return error_msg, f"💡 An error occurred during processing.", None


# --- HR JOB POSTING FUNCTIONS (MODIFIED to use more distinct ID) ---

def post_job(title, company, description):
    if not title or not company or not description:
        # Return updates for all relevant components
        return gr.update(value=title), gr.update(value=company), gr.update(value=description), view_jobs_markdown(), f"❌ Error: All job fields are required to post.", gr.update(choices=list(JOB_POSTINGS.keys()), value=None), gr.update(choices=list(JOB_POSTINGS.keys()), value=None)

    job_id = f"{company.upper()[:3]}-{random.randint(100, 999)}-{int(time.time()) % 1000}"
    JOB_POSTINGS[job_id] = {
        "title": title,
        "company": company,
        "description": description,
        "posted_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    job_keys = list(JOB_POSTINGS.keys())
    
    # Update job_dropdown and ats_job_dropdown
    return gr.update(value=""), gr.update(value=""), gr.update(value=""), view_jobs_markdown(), f"✅ Success! Job **'{title}'** posted with ID: **{job_id}**", gr.update(choices=job_keys), gr.update(choices=job_keys)

def view_jobs_markdown():
    if not JOB_POSTINGS:
        return "No job postings available at this time."
        
    job_list_markdown = "### Available Job Openings\n"
    for jid, job in JOB_POSTINGS.items():
        job_list_markdown += f"#### {job['title']} at {job['company']}\n"
        job_list_markdown += f"**ID:** `{jid}` | **Posted:** {job['posted_at']}\n"
        truncated_desc = job['description'][:150].replace('\n', ' ') + ("..." if len(job['description']) > 150 else "")
        job_list_markdown += f"{truncated_desc}\n\n"
    return job_list_markdown


# --- APPLICANT INTERACTION FUNCTIONS (SIMPLIFIED) ---

def select_job_details(job_id):
    """Returns the description markdown for a selected job for the main job listing view."""
    if job_id and job_id in JOB_POSTINGS:
        job = JOB_POSTINGS[job_id]
        details = (
            f"### {job['title']} at {job['company']}\n"
            f"**Job ID:** {job_id}\n"
            f"**Posted:** {job['posted_at']}\n\n"
            f"**Description:**\n{job['description']}"
        )
        return details
    return "Please select a job ID to view the full description."

def get_job_description_for_ats(job_id):
    """Returns the raw job description text for the ATS input box."""
    if job_id and job_id in JOB_POSTINGS:
        return JOB_POSTINGS[job_id]['description']
    return "Select a job ID to load the description."

# --- NEW: FILE READING UTILITY FUNCTION ---

def read_resume_file(file):
    """Reads the content of an uploaded file (supports basic text or a mock .docx read)."""
    if file is None:
        return None, "Upload a .txt or .docx file to extract resume text.", None

    file_path = file.name
    filename = os.path.basename(file_path)
    
    try:
        if filename.endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content, f"✅ Text extracted from **{filename}** (.txt).", gr.update(value=content, lines=15)
        
        elif filename.endswith('.docx'):
            # Mock or simplified docx read - real implementation is complex
            doc = Document(file_path)
            content_parts = []
            for para in doc.paragraphs:
                content_parts.append(para.text)
            content = "\n\n".join(content_parts)
            
            if not content.strip():
                return None, "⚠️ Could not extract text from .docx. Try a .txt or copy/paste the text.", gr.update(lines=15)

            return content, f"✅ Text extracted from **{filename}** (.docx). **Review/Edit below.**", gr.update(value=content, lines=15)
        
        else:
            return None, "❌ Unsupported file format. Please upload a **.txt** or **.docx** file.", gr.update(lines=15)
            
    except Exception as e:
        return None, f"❌ Error reading file: {e}", gr.update(lines=15)

# --- NEW: ATS SCORE CALCULATION FUNCTION (Enhanced with Improvement Tips) ---

def calculate_ats_score(resume_text, job_id, ats_job_desc_out_value):
    if not job_id or job_id not in JOB_POSTINGS:
        return "❌ **Error**: Please select a valid Job ID first.", gr.update(value=ats_job_desc_out_value)

    if not resume_text:
        return "❌ **Error**: Please upload your resume file and ensure text is extracted or paste resume text to check the score.", gr.update(value=ats_job_desc_out_value)

    job_description = JOB_POSTINGS[job_id]['description'].lower()
    resume_lower = resume_text.lower()
    
    # 1. Keyword Extraction (simplistic but effective mock)
    stop_words = set(['and', 'the', 'a', 'an', 'is', 'to', 'in', 'of', 'with', 'for', 'you', 'we', 'are', 'be', 'at', 'by', 'on', 'our', 'this', 'that', 'from', 'as', 'will', 'must', 'skills', 'experience', 'ability', 'work', 'data', 'using', 'job', 'role', 'team', 'etc', 'etc.', 'project', 'projects', 'strong', 'proven', 'drive', 'results']) # Added more stop words
    
    # Extract keywords (>= 4 characters, not a stop word)
    job_keywords = set(re.findall(r'\b\w{4,}\b', job_description))
    job_keywords = {word for word in job_keywords if word not in stop_words and not word.isdigit()}
    
    resume_keywords = set(re.findall(r'\b\w{4,}\b', resume_lower))
    
    # 2. Score Calculation
    matched_keywords = job_keywords.intersection(resume_keywords)
    missing_keywords = job_keywords.difference(resume_keywords)
    
    total_job_keywords = len(job_keywords)
    matched_count = len(matched_keywords)
    
    if total_job_keywords == 0:
        return "⚠️ **ATS Error**: Job description is too generic for meaningful scoring.", gr.update(value=ats_job_desc_out_value)

    # Match percentage, then adjust to a 100 point scale (max 95)
    match_percentage = (matched_count / total_job_keywords) * 100
    ats_score = min(95, int(match_percentage * 1.5 + 40)) 
    
    if ats_score < 40: ats_score = random.randint(30, 45) # Min score limit

    match_list = "\n- ".join(matched_keywords)
    missing_list_sample = "\n- ".join(list(missing_keywords)[:5])
    
    # 3. Improvement Tips/Guidance
    improvement_tips = []
    if ats_score < 60:
        improvement_tips.append(f"**Action 1: Address Missing Keywords.** Try integrating terms like **{', '.join(list(missing_keywords)[:3])}** into your experience or skills section.")
    
    if 'leadership' in job_keywords and 'leadership' not in resume_keywords:
        improvement_tips.append("**Action 2: Soft Skills.** Quantify your leadership or teamwork experiences. E.g., 'Led a team of 4...'")
        
    if re.search(r'\d+%|\d+\s+million', resume_text) is None:
        improvement_tips.append("**Action 3: Use Metrics.** Use numbers (e.g., percentages, counts) in your bullet points to show impact. *Quantify your achievements!*")
        
    if not improvement_tips:
        improvement_tips.append("Your resume is well-tailored! Focus on interview preparation.")
        
    
    # 4. Final Output Construction
    output = f"## 🤖 ATS Match Score: **{ats_score}%**\n\n"
    
    if ats_score >= 80:
        output += "🎉 **Excellent Match!** Your resume is highly tailored to this job. Expect strong visibility."
    elif ats_score >= 60:
        output += "👍 **Good Match.** Your resume covers many key areas. Consider adding more keywords from the description."
    else:
        output += "⚠️ **Moderate Match.** Your resume is missing several key job keywords. Review the job description and tailor your skills and experience sections."
        
    output += f"\n\n---\n\n### Matched Keywords ({matched_count}/{total_job_keywords}):\n- {match_list if match_list else 'None matched.'}"
    
    if missing_keywords:
        output += f"\n\n### Top Missing Keywords (Potential Improvement):\n- {missing_list_sample}..."

    output += "\n\n---\n\n### 🚀 **Tailoring & Improvement Tips**\n"
    output += "\n".join([f"**Tip:** {tip}" for tip in improvement_tips])
    
    return output, gr.update(value=get_job_description_for_ats(job_id))


# --- GRADIO INTERFACE SETUP ---

custom_css = """
.gradio-container { background: #f0f0f0; }
.textbox-bordered { border: 3px solid #1E3A8A; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.2); }
.custom-run-button { background-color: #0072CE !important; color: white !important; font-weight: bold; border-radius: 8px; padding: 10px 20px; }
.hr-header { color: #D61B1F; font-size: 1.5em; font-weight: bold; }
.applicant-header { color: #0072CE; font-size: 1.5em; font-weight: bold; }
.auth-title { color: #1E3A8A; font-size: 2em; }
"""

with gr.Blocks(css=custom_css) as demo:
    
    # --- State Variables ---
    auth_state = gr.State((None, "guest"))
    extracted_resume_text = gr.State("") # State to hold extracted text between steps
    
    gr.Markdown("# 🏢 IBM Granite AI Career Portal")

    # 1. Define all Components
    with gr.Tabs() as main_tabs:
        
        # --- TAB 1: LOGIN / REGISTER (Unchanged) ---
        with gr.TabItem("Authentication", elem_id="auth_tab") as auth_tab:
            gr.Markdown("<div class='auth-title'>Access Portal</div>")
            login_status_msg = gr.Markdown("Please login or register to use the portals.")
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 📝 New User Registration")
                    reg_user = gr.Textbox(label="Username")
                    reg_pass = gr.Textbox(label="Password", type="password")
                    reg_role = gr.Radio(["student", "hr"], label="Account Type")
                    register_btn = gr.Button("Register Account", variant="secondary")
                    reg_message = gr.Markdown("")
                    
                with gr.Column(scale=1):
                    gr.Markdown("### 🔑 Existing User Login")
                    login_user = gr.Textbox(label="Username")
                    login_pass = gr.Textbox(label="Password", type="password")
                    login_btn = gr.Button("Login to Portal", variant="primary")
        
        # --- TAB 2: APPLICANT PORTAL (ATS Tab Added) ---
        with gr.TabItem("Applicant Portal", visible=False) as applicant_tab:
            
            gr.Markdown("<div class='applicant-header'>AI Resume Generation & Tools</div>")
            
            with gr.Tabs():
                
                # --- SUB-TAB 1: RESUME BUILDER ---
                with gr.TabItem("Resume Builder"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            gr.Markdown("### 👤 Personal Details & Resume Builder")
                            name = gr.Textbox(label="Full Name")
                            with gr.Row():
                                email_id = gr.Textbox(label="Email id")
                                contact_no = gr.Textbox(label="Contact no")
                            linkedin_url = gr.Textbox(label="LinkedIn URL")
                            gr.Markdown("---")
                            objective = gr.Textbox(label="Career Objective", lines=3, placeholder="To leverage my skills...")
                            skills = gr.Textbox(label="Key Skills (Programming/Tech)")
                            education = gr.Textbox(label="Education", lines=2)
                            gr.Markdown("---")
                            experience = gr.Textbox(label="Internships / Experience", lines=3, placeholder="List your internships and professional roles here.")
                            projects_input = gr.Textbox(label="Projects", lines=3, placeholder="Separate projects with a new line or bullet points.")
                            certifications_input = gr.Textbox(label="Certifications", lines=2, placeholder="List certifications separated by new lines.")
                            gr.Markdown("---")
                            prompt_extra = gr.Textbox(label="Additional Instructions for AI", lines=1, placeholder="e.g., Focus on leadership skills for a managerial role."
                                                      ) 
                            run = gr.Button("✨ Generate Professional Resume", elem_classes=["custom-run-button"])
                        
                        with gr.Column(scale=2):
                            gr.Markdown("### Resume Output")
                            with gr.Tab("AI Generated Text"):
                                resume_out = gr.Textbox(label="📄 Review AI Generated Text (LLM Raw Output)", lines=10, elem_classes=["textbox-bordered"])
                            with gr.Tab("Guidance"):
                                guidance_out = gr.Markdown("💡 Guidance and Tips will appear here after generation.")
                            
                            download = gr.File(label="⬇️ Download Formatted .docx File")

                # --- SUB-TAB 2: JOB DETAILS & LISTING (Unchanged) ---
                with gr.TabItem("Job Listings"):
                    gr.Markdown("### 📜 Job Listing Details")
                    with gr.Row():
                        with gr.Column(scale=1):
                            job_summary = gr.Markdown(view_jobs_markdown(), label="Job Summary List")
                            
                        with gr.Column(scale=2):
                            gr.Markdown("#### Select a Job ID to view the full description")
                            job_dropdown = gr.Dropdown(
                                choices=[], 
                                label="Select Job ID",
                                interactive=True
                            )
                            job_description_out = gr.Markdown("Select a job ID from the dropdown to view the description.")
                
                # --- SUB-TAB 3: ATS SCORE CHECK (MODIFIED) ---
                with gr.TabItem("ATS Score Check"):
                    gr.Markdown("### 🎯 Resume ATS Match Checker")
                    gr.Markdown("Select a job, upload your resume file (.txt or .docx), and check the ATS score to optimize your application.")
                    
                    with gr.Row():
                        with gr.Column(scale=1):
                            ats_job_dropdown = gr.Dropdown(
                                choices=[], 
                                label="1. Select Target Job ID",
                                interactive=True
                            )
                            gr.Markdown("#### Job Description (Read-only)")
                            ats_job_desc_out = gr.Textbox(label="", lines=10, interactive=False, value="Select a job ID to load the description.")
                            
                            gr.Markdown("---")
                            ats_resume_upload = gr.File(
                                label="2. Upload Resume File (.txt or .docx)",
                                file_types=[".txt", ".docx"],
                                interactive=True
                            )
                            file_status_msg = gr.Markdown("Upload status will appear here.")
                            extract_btn = gr.Button("Extract Text from File", variant="secondary")
                            
                        with gr.Column(scale=2):
                            ats_resume_text_edit = gr.Textbox(
                                label="3. Extracted Resume Text (Review & Edit)", 
                                lines=12, 
                                placeholder="Extracted resume text will appear here. Edit it to improve your score.",
                                elem_classes=["textbox-bordered"]
                            )
                            check_ats_btn = gr.Button("🔍 Check ATS Score", variant="primary")
                            ats_score_out = gr.Markdown("Score and keyword analysis will appear here.")


            logout_btn_applicant = gr.Button("Logout", variant="secondary")

        # --- TAB 3: HR PORTAL (Unchanged Structure) ---
        with gr.TabItem("HR Portal", visible=False) as hr_tab:
            
            gr.Markdown("<div class='hr-header'>HR Management Portal: Post New Job Applications</div>")
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 📋 Post New Job")
                    job_title = gr.Textbox(label="Job Title", placeholder="e.g., Senior Data Scientist")
                    job_company = gr.Textbox(label="Company Name", placeholder="e.g., IBM")
                    job_description = gr.Textbox(label="Job Description", lines=5, placeholder="Paste the full job description here.")
                    post_btn = gr.Button("Post Job", variant="primary")
                    posting_message = gr.Markdown("Job posting status will appear here.")
                    
                with gr.Column(scale=2):
                    gr.Markdown("### 📜 Current Active Job Postings")
                    current_jobs_out = gr.Markdown(view_jobs_markdown(), visible=True)

            logout_btn_hr = gr.Button("Logout", variant="secondary")
            
    
    # 2. Define all Event Handlers (Click functions)

    # --- Registration Logic (Unchanged) ---
    register_btn.click(
        register_user,
        inputs=[reg_user, reg_pass, reg_role],
        outputs=[reg_message, reg_user, reg_pass, reg_role, login_user, login_pass]
    )
    
    # --- Login Logic (Updates both job_dropdowns for Applicant Portal) ---
    login_btn.click(
        user_login,
        inputs=[login_user, login_pass],
        outputs=[auth_state, login_status_msg, applicant_tab, hr_tab, auth_tab, job_dropdown, job_summary, ats_job_dropdown]
    )

    # --- Applicant Resume Generation Logic (Unchanged) ---
    run.click(
        generate_resume,
        inputs=[
            name, email_id, contact_no, linkedin_url, objective, skills, 
            education, experience, projects_input, certifications_input, prompt_extra
        ],
        outputs=[resume_out, guidance_out, download] 
    )
    
    # --- Job Listing Interaction Logic (Unchanged) ---
    job_dropdown.change(
        select_job_details,
        inputs=[job_dropdown],
        outputs=[job_description_out]
    )
    
    # --- ATS Interaction Logic (MODIFIED) ---
    ats_job_dropdown.change(
        get_job_description_for_ats,
        inputs=[ats_job_dropdown],
        outputs=[ats_job_desc_out]
    )
    
    # Step 1: Extract Text
    extract_btn.click(
        read_resume_file,
        inputs=[ats_resume_upload],
        outputs=[extracted_resume_text, file_status_msg, ats_resume_text_edit]
    )
    
    # Step 2: Calculate Score using the text from the editable box
    check_ats_btn.click(
        calculate_ats_score,
        # Now uses the user-editable/reviewable text box content
        inputs=[ats_resume_text_edit, ats_job_dropdown, ats_job_desc_out],
        outputs=[ats_score_out, ats_job_desc_out] 
    )
    
    # --- HR Post Job Logic (Updates HR components and BOTH applicant dropdowns) ---
    post_btn.click(
        post_job,
        inputs=[job_title, job_company, job_description],
        # Outputs: job_title, job_company, job_description, current_jobs_out, posting_message, job_dropdown, ats_job_dropdown
        outputs=[job_title, job_company, job_description, current_jobs_out, posting_message, job_dropdown, ats_job_dropdown]
    ).then(
        view_jobs_markdown, 
        inputs=[],
        # Update Applicant Summary list
        outputs=[job_summary] 
    )
    
    # --- LOGOUT Logic (Shared) ---
    logout_btn_applicant.click(
        user_logout,
        inputs=[],
        outputs=[auth_state, login_status_msg, applicant_tab, hr_tab, auth_tab]
    )
    
    logout_btn_hr.click(
        user_logout,
        inputs=[],
        outputs=[auth_state, login_status_msg, applicant_tab, hr_tab, auth_tab]
    )

demo.launch()
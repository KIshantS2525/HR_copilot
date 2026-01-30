# import sys
# import os

# ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# sys.path.append(ROOT_DIR)

# import streamlit as st
# from backend.vectorstore import build_vectorstore
# from backend.retrieval import retrieve
# from backend.intent import is_greeting, is_vague_question
# from backend.llm import ask_qwen
# from backend.config import HR_FALLBACK_MESSAGE

# st.set_page_config(page_title="HR Policy Copilot", layout="wide")
# st.title("🧑‍💼 HR Policy Copilot")

# if "chat_history" not in st.session_state:
#     st.session_state.chat_history = []

# if "clarification_count" not in st.session_state:
#     st.session_state.clarification_count = 0

# @st.cache_resource
# def load_store():
#     return build_vectorstore()

# index, chunks, sources, embedder = load_store()

# for msg in st.session_state.chat_history:
#     with st.chat_message(msg["role"]):
#         st.write(msg["content"])

# query = st.chat_input("Ask anything about HR policies...")

# if query:
#     st.session_state.chat_history.append({"role": "user", "content": query})
#     with st.chat_message("user"):
#         st.write(query)

#     if is_greeting(query):
#         reply = "Hello! 👋 How may I assist you with HR policies today?"
#         st.chat_message("assistant").write(reply)
#         st.session_state.chat_history.append({"role": "assistant", "content": reply})
#         st.stop()

#     if is_vague_question(query):
#         st.session_state.clarification_count += 1
#         if st.session_state.clarification_count <= 3:
#             reply = "Could you please provide a bit more detail?"
#         else:
#             reply = HR_FALLBACK_MESSAGE

#         st.chat_message("assistant").write(reply)
#         st.session_state.chat_history.append({"role": "assistant", "content": reply})
#         st.stop()

#     st.session_state.clarification_count = 0

#     with st.chat_message("assistant"):
#         typing = st.empty()
#         typing.markdown("_HR Assistant is typing…_")

#         docs = retrieve(query, index, chunks, sources, embedder)

#         if not docs:
#             typing.markdown(HR_FALLBACK_MESSAGE)
#             st.session_state.chat_history.append(
#                 {"role": "assistant", "content": HR_FALLBACK_MESSAGE}
#             )
#             st.stop()

#         answer = ask_qwen(query, docs, st.session_state.chat_history)
#         typing.markdown(answer)

#     st.session_state.chat_history.append(
#         {"role": "assistant", "content": answer}
#     )


# --------------------------------------------------------





# import sys
# import os
# import streamlit as st
# from hr_validator import validate_hr_question



# ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# sys.path.append(ROOT_DIR)

# from vectorstore import build_vectorstore
# from retrieval import retrieve
# from intent_router import handle_query   # ✅ single LLM brain
# from config import HR_FALLBACK_MESSAGE

# # ---------------- PAGE CONFIG ----------------
# st.set_page_config(page_title="Ascentt HR Copilot", layout="wide")

# # ---------------- HEADER ----------------
# st.markdown("""
# <div style="text-align:center; padding:20px 0;">
#     <h1 style="color:#F57C00; margin-bottom:5px;">🤖 Ascentt HR Copilot</h1>
#     <p style="color:#6B6B6B; font-size:16px;">
#         Your centralized assistant for HR policies, leave, and employee benefits.
#     </p>
# </div>
# """, unsafe_allow_html=True)

# # ---------------- CUSTOM CSS ----------------
# st.markdown("""
# <style>
# body, .main { background-color:#F7F7F7; }

# .chat-user {
#     background:#F57C00;
#     color:white;
#     padding:12px 16px;
#     border-radius:16px;
#     margin:10px 0 10px auto;
#     max-width:65%;
# }

# .chat-bot {
#     background:#FFFFFF;
#     color:#1F1F1F;
#     padding:12px 16px;
#     border-radius:16px;
#     margin:10px auto 10px 0;
#     max-width:65%;
#     border:1px solid #E0E0E0;
# }

# .typing {
#     background:#FFFFFF;
#     color:#6B6B6B;
#     padding:10px 16px;
#     border-radius:16px;
#     border:1px dashed #E0E0E0;
#     width:fit-content;
# }
# </style>
# """, unsafe_allow_html=True)

# # ---------------- SESSION STATE ----------------
# if "messages" not in st.session_state:
#     st.session_state.messages = []

# if "show_hero" not in st.session_state:
#     st.session_state.show_hero = True

# # ---------------- SIDEBAR ----------------
# with st.sidebar:
#     st.markdown("### ⚙️ Options")
#     if st.button("🗑️ Clear conversation"):
#         st.session_state.messages = []
#         st.session_state.show_hero = True
#         st.rerun()

# # ---------------- HERO SECTION ----------------
# if st.session_state.show_hero:
#     st.markdown("<p style='text-align:center;'><b>Suggested Questions</b></p>", unsafe_allow_html=True)
#     c1, c2, c3 = st.columns(3)

#     if c1.button("📄 Sick leave policy"):
#         st.session_state.messages.append(
#             {"role": "user", "content": "What is the sick leave policy?"}
#         )
#         st.session_state.show_hero = False
#         st.rerun()

#     if c2.button("⚖️ POSH complaint process"):
#         st.session_state.messages.append(
#             {"role": "user", "content": "What is the POSH complaint process?"}
#         )
#         st.session_state.show_hero = False
#         st.rerun()

#     if c3.button("🏖️ Leave eligibility"):
#         st.session_state.messages.append(
#             {"role": "user", "content": "What are the leave eligibility rules?"}
#         )
#         st.session_state.show_hero = False
#         st.rerun()

# # ---------------- LOAD VECTORSTORE ----------------
# @st.cache_resource
# def load_store():
#     return build_vectorstore()

# index, chunks, sources, embedder = load_store()

# # ---------------- RENDER CHAT ----------------
# for msg in st.session_state.messages:
#     if msg["role"] == "user":
#         st.markdown(
#             f"<div class='chat-user'>{msg['content']}</div>",
#             unsafe_allow_html=True
#         )
#     else:
#         st.markdown(
#             f"<div class='chat-bot'>{msg['content']}</div>",
#             unsafe_allow_html=True
#         )

# # ---------------- INPUT ----------------
# query = st.chat_input("Ask a question...")

# if query:
#     st.session_state.show_hero = False
#     st.session_state.messages.append(
#         {"role": "user", "content": query}
#     )
#     st.rerun()

# # ---------------- ASSISTANT RESPONSE ----------------
# if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":

#     typing = st.empty()
#     typing.markdown(
#         "<div class='typing'>🤖 HR Copilot is thinking...</div>",
#         unsafe_allow_html=True
#     )

#     user_query = st.session_state.messages[-1]["content"]

#     # 🔍 Always retrieve docs (LLM decides whether to use them)
#     docs = retrieve(user_query, index, chunks, sources, embedder)

#     try:
#         answer = handle_query(
#             query=user_query,
#             chat_history=st.session_state.messages,
#             docs=docs
#         )
#     except Exception:
#         answer = HR_FALLBACK_MESSAGE

#     typing.empty()
#     st.session_state.messages.append(
#         {"role": "assistant", "content": answer}
#     )
#     st.rerun()



import sys
import os
import streamlit as st

# ---------------- PATH SETUP ----------------
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(ROOT_DIR)

# ---------------- IMPORTS ----------------
from hr_validator import validate_hr_question
from vectorstore import build_vectorstore
from retrieval import retrieve
from intent_router import handle_query
from config import HR_FALLBACK_MESSAGE, NHR_FALLBACK_MESSAGE

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="Ascentt HR Copilot", layout="wide")

# ---------------- HEADER ----------------
st.markdown("""
<div style="text-align:center; padding:20px 0;">
    <h1 style="color:#F57C00; margin-bottom:5px;">🤖 Ascentt HR Copilot</h1>
    <p style="color:#6B6B6B; font-size:16px;">
        Your centralized assistant for HR policies, leave, and employee benefits.
    </p>
</div>
""", unsafe_allow_html=True)

# ---------------- CUSTOM CSS ----------------
st.markdown("""
<style>
body, .main { background-color:#F7F7F7; }

.chat-user {
    background:#F57C00;
    color:white;
    padding:12px 16px;
    border-radius:16px;
    margin:10px 0 10px auto;
    max-width:65%;
}

.chat-bot {
    background:#FFFFFF;
    color:#1F1F1F;
    padding:12px 16px;
    border-radius:16px;
    margin:10px auto 10px 0;
    max-width:65%;
    border:1px solid #E0E0E0;
}

.typing {
    background:#FFFFFF;
    color:#6B6B6B;
    padding:10px 16px;
    border-radius:16px;
    border:1px dashed #E0E0E0;
    width:fit-content;
}
</style>
""", unsafe_allow_html=True)

# ---------------- SESSION STATE ----------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "show_hero" not in st.session_state:
    st.session_state.show_hero = True

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.markdown("### ⚙️ Options")
    if st.button("🗑️ Clear conversation"):
        st.session_state.messages = []
        st.session_state.show_hero = True
        st.rerun()

# ---------------- HERO SECTION ----------------
if st.session_state.show_hero:
    st.markdown("<p style='text-align:center;'><b>Suggested Questions</b></p>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)

    if c1.button("📄 Sick leave policy"):
        st.session_state.messages.append(
            {"role": "user", "content": "What is the sick leave policy?"}
        )
        st.session_state.show_hero = False
        st.rerun()

    if c2.button("⚖️ POSH complaint process"):
        st.session_state.messages.append(
            {"role": "user", "content": "What is the POSH complaint process?"}
        )
        st.session_state.show_hero = False
        st.rerun()

    if c3.button("🏖️ Leave eligibility"):
        st.session_state.messages.append(
            {"role": "user", "content": "What are the leave eligibility rules?"}
        )
        st.session_state.show_hero = False
        st.rerun()

# ---------------- LOAD VECTORSTORE ----------------
@st.cache_resource
def load_store():
    return build_vectorstore()

index, chunks, sources, embedder = load_store()

# ---------------- RENDER CHAT ----------------
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(
            f"<div class='chat-user'>{msg['content']}</div>",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"<div class='chat-bot'>{msg['content']}</div>",
            unsafe_allow_html=True
        )

# ---------------- INPUT ----------------
query = st.chat_input("Ask a question...")

if query:
    st.session_state.show_hero = False
    st.session_state.messages.append(
        {"role": "user", "content": query}
    )
    st.rerun()

# ---------------- ASSISTANT RESPONSE ----------------
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":

    typing = st.empty()
    typing.markdown(
        "<div class='typing'>🤖 HR Copilot is thinking...</div>",
        unsafe_allow_html=True
    )

    user_query = st.session_state.messages[-1]["content"]

    # ✅ STEP 1: HR VALIDATION
    validation = validate_hr_question(user_query)

    if not validation["is_hr"]:
        # 🚫 NON-HR → fallback
        answer = NHR_FALLBACK_MESSAGE
    else:
        # ✅ HR → RAG + Intent Router
        try:
            docs = retrieve(user_query, index, chunks, sources, embedder)
            answer = handle_query(
                query=user_query,
                chat_history=st.session_state.messages,
                docs=docs
            )
        except Exception:
            answer = HR_FALLBACK_MESSAGE

    typing.empty()
    st.session_state.messages.append(
        {"role": "assistant", "content": answer}
    )
    st.rerun()

import streamlit as st
import random


# ---------------- Page Config ----------------

st.set_page_config(
    page_title="Secure Code Generator",
    page_icon="🔑",
    layout="wide"
)


# ---------------- Style ----------------

st.markdown("""
<style>

.stApp {
    background-color:#0b0f19;
    color:white;
}

.title {
    text-align:center;
    font-size:40px;
    font-weight:bold;
    color:#3b82f6;
}

.code-box {
    background:#111827;
    border:1px solid #2563eb;
    padding:10px;
    border-radius:8px;
    font-family:monospace;
    font-size:18px;
    margin:5px;
}

</style>
""", unsafe_allow_html=True)



# ---------------- Allowed Characters ----------------

ALLOWED_CHARS = (
    "BCDFGHJKMNPQRVWXYZ"
    "2346789"
)


# ---------------- Generator ----------------

def generate_single_code():

    parts = []

    for _ in range(5):

        part = "".join(
            random.choice(ALLOWED_CHARS)
            for _ in range(5)
        )

        parts.append(part)


    return "-".join(parts)



def generate_codes(amount):

    codes = []

    for _ in range(amount):

        codes.append(
            generate_single_code()
        )

    return codes



# ---------------- Interface ----------------

st.markdown(
    "<div class='title'>🔑 Secure Code Generator</div>",
    unsafe_allow_html=True
)


st.write(
    "مولد أكواد بتنسيق 5×5 باستخدام الرموز المسموحة فقط."
)



st.divider()



amount = st.number_input(
    "عدد الأكواد المطلوبة:",
    min_value=1,
    max_value=10000,
    value=20,
    step=10
)



if st.button(
    "🚀 توليد الأكواد",
    use_container_width=True
):

    generated = generate_codes(amount)


    st.success(
        f"تم توليد {len(generated)} كود"
    )


    st.subheader(
        "📋 الأكواد:"
    )


    for code in generated:

        st.markdown(
            f"""
            <div class="code-box">
            🔑 {code}
            </div>
            """,
            unsafe_allow_html=True
        )



# ---------------- Info ----------------

with st.sidebar:

    st.header("⚙️ معلومات")

    st.write(
        """
        **البنية:**

        XXXXX-XXXXX-XXXXX-XXXXX-XXXXX


        **عدد الرموز:**

        25 رمزاً


        **المسموح:**

        B C D F G H J K M N P Q R V W X Y Z

        2 3 4 6 7 8 9
        """
    )

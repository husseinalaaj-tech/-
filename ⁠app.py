import re
import urllib.parse
import requests
import streamlit as st

# ------------------------------------------------------------------------------
# 1. Page Configuration & Custom CSS (Dark Recon Console Theme)
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="Instagram OSINT Recon Console",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Dark Recon Aesthetics
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Inter:wght@400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    code, .stCodeBlock, [data-testid="stCodeBlock"] {
        font-family: 'JetBrains Mono', monospace !important;
    }

    .disclaimer-box {
        background-color: #1e1e2e;
        border-left: 4px solid #f38ba8;
        padding: 14px 18px;
        border-radius: 6px;
        margin-bottom: 20px;
        color: #cdd6f4;
        font-size: 0.9em;
    }

    .dork-card {
        background-color: #181825;
        border: 1px solid #313244;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 20px;
    }

    .google-btn {
        display: inline-block;
        background-color: #89b4fa;
        color: #11111b !important;
        font-weight: 600;
        padding: 8px 16px;
        border-radius: 6px;
        text-decoration: none;
        margin-top: 10px;
        transition: background-color 0.2s ease;
    }

    .google-btn:hover {
        background-color: #b4befe;
        text-decoration: none;
    }
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------------------
# 2. Helper Functions: Sanitization & API Logic
# ------------------------------------------------------------------------------
def sanitize_username(raw_input: str) -> tuple[str, bool]:
    """
    Strips whitespace, @ prefix, invalid chars outside [A-Za-z0-9._],
    and truncates to Instagram's 30-character limit.
    """
    if not raw_input:
        return "", False
    
    cleaned = raw_input.strip().lstrip('@')
    cleaned = re.sub(r'[^A-Za-z0-9._]', '', cleaned)
    cleaned = cleaned[:30]
    
    is_modified = (cleaned != raw_input)
    return cleaned, is_modified


def fetch_google_custom_search(query: str, api_key: str, cx: str) -> tuple[list | None, str | None]:
    """
    Queries Google Custom Search API and returns (results_list, error_message).
    Handles timeouts, connection failures, quota limits, and bad keys cleanly.
    """
    endpoint = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": api_key,
        "cx": cx,
        "q": query
    }

    try:
        response = requests.get(endpoint, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            return items, None

        # Parse specific status codes and JSON error responses
        try:
            err_json = response.json()
            message = err_json.get("error", {}).get("message", "Unknown API error")
            reason = err_json.get("error", {}).get("errors", [{}])[0].get("reason", "")
        except Exception:
            message = response.text
            reason = ""

        if response.status_code == 400:
            return None, f"HTTP 400 (Bad Request): Please check your Custom Search Engine ID (CX). Details: {message}"
        elif response.status_code == 403:
            if "quota" in reason.lower() or "limit" in message.lower():
                return None, "HTTP 403: Google Custom Search API daily quota exceeded."
            return None, f"HTTP 403 (Forbidden): Invalid API Key or access restricted. Details: {message}"
        elif response.status_code == 429:
            return None, "HTTP 429: Rate limit exceeded. Please wait a moment before trying again."
        else:
            return None, f"HTTP {response.status_code} Error: {message}"

    except requests.exceptions.Timeout:
        return None, "Network Error: Request timed out (10s). Check your internet connection."
    except requests.exceptions.ConnectionError:
        return None, "Network Error: Failed to connect to Google API servers."
    except requests.exceptions.JSONDecodeError:
        return None, "Parse Error: Received an invalid JSON response from the server."
    except Exception as e:
        return None, f"Unexpected Error: {str(e)}"


# ------------------------------------------------------------------------------
# 3. Sidebar Configuration (API Credentials)
# ------------------------------------------------------------------------------
st.sidebar.title("⚙️ API Configuration")
st.sidebar.markdown("Optional integration for live in-app Google search results.")

use_api = st.sidebar.checkbox("Enable Live Search API", value=False)

api_key = ""
cx_id = ""

if use_api:
    # Attempt to load credentials from Streamlit Secrets if available
    default_key = st.secrets.get("GOOGLE_API_KEY", "") if "GOOGLE_API_KEY" in st.secrets else ""
    default_cx = st.secrets.get("GOOGLE_CX", "") if "GOOGLE_CX" in st.secrets else ""

    api_key = st.sidebar.text_input("Google API Key", value=default_key, type="password")
    cx_id = st.sidebar.text_input("Custom Search Engine ID (CX)", value=default_cx)
    
    if not api_key or not cx_id:
        st.sidebar.warning("⚠️ Enter both API Key and CX ID to enable live snippet fetching.")
    else:
        st.sidebar.success("✅ Credentials configured.")

# Initialize Session State for caching search results
if "api_cache" not in st.session_state:
    st.session_state.api_cache = {}


# ------------------------------------------------------------------------------
# 4. Main Interface Header & Explainer
# ------------------------------------------------------------------------------
st.title("🔍 Instagram OSINT Recon Console")
st.markdown("Automated Google Search Operators (Dorks) Generator for public profile investigation.")

with st.expander("ℹ️ How This Tool Works & OSINT Methodology"):
    st.markdown("""
    This utility generates targeted **Google Search Operators (Dorks)** to query publicly indexed Instagram data stored in Google's web caches.
    
    * **`site:instagram.com/p/`**: Narrows scope to public post URL paths where comments exist.
    * **`site:instagram.com/reel/`**: Isolates Reels interactions and mentions.
    * **`"username"`**: Enforces exact match string searching.
    * **`-inurl:username`**: Excludes the user's primary profile page to highlight external interactions.
    
    *Note: This tool queries publicly archived search data only and does not bypass private account boundaries.*
    """)

st.markdown("""
<div class="disclaimer-box">
    <strong>⚖️ Ethical & Legal Disclaimer:</strong> This application is intended strictly for authorized security research, OSINT gathering on public assets, and educational analysis. Users must comply with applicable terms of service and legal regulations.
</div>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------------------
# 5. Input Processing & Sanitization
# ------------------------------------------------------------------------------
raw_username = st.text_input("Enter Target Instagram Username:", placeholder="e.g. rrenguk")

target_username, was_sanitized = sanitize_username(raw_username)

if raw_username and was_sanitized:
    st.info(f"🧹 **Sanitized Input:** Converted `{raw_username}` ➔ `{target_username}` (stripped spaces/@/invalid chars, truncated to 30 chars).")

if target_username:
    st.divider()
    st.subheader(f"🎯 Recon Target: `{target_username}`")

    # Define the 4 exact Dork categories
    dorks = [
        {
            "id": "comments",
            "title": "1. Comments on External Posts",
            "desc": "Finds public comments made by or referencing the user on other accounts' posts.",
            "query": f'site:instagram.com/p/ "{target_username}" -inurl:{target_username}'
        },
        {
            "id": "reels",
            "title": "2. Reels Interactions & Mentions",
            "desc": "Discovers public Reels videos mentioning or tagging the target user.",
            "query": f'site:instagram.com/reel/ "{target_username}" -inurl:{target_username}'
        },
        {
            "id": "mentions",
            "title": "3. General Public Mentions",
            "desc": "Broad search for any public Instagram page referencing the target username.",
            "query": f'site:instagram.com "{target_username}" -inurl:{target_username}'
        },
        {
            "id": "profile",
            "title": "4. Profile & Bio Indexing",
            "desc": "Inspects Google's indexed cache of the target's primary profile page.",
            "query": f'site:instagram.com/{target_username}'
        }
    ]

    # Render Dork Cards
    for category in dorks:
        dork_id = category["id"]
        title = category["title"]
        desc = category["desc"]
        query = category["query"]
        
        encoded_query = urllib.parse.quote(query)
        google_url = f"https://www.google.com/search?q={encoded_query}"

        st.markdown(f"#### {title}")
        st.caption(desc)
        
        # Code display box with built-in copy button
        st.code(query, language="text")
        
        col_btn1, col_btn2 = st.columns([1, 4])
        
        with col_btn1:
            st.markdown(f'<a href="{google_url}" target="_blank" class="google-btn">🌐 Open in Google</a>', unsafe_allow_html=True)
            
        with col_btn2:
            # API Snippet Fetching logic
            api_button_disabled = not (use_api and api_key and cx_id)
            btn_key = f"btn_{target_username}_{dork_id}"
            
            if st.button("📡 Fetch Live Snippets", key=btn_key, disabled=api_button_disabled):
                with st.spinner("Querying Google Custom Search API..."):
                    results, error = fetch_google_custom_search(query, api_key, cx_id)
                    cache_key = f"{target_username}_{dork_id}"
                    st.session_state.api_cache[cache_key] = {"results": results, "error": error}

        # Display cached API results if present
        cache_key = f"{target_username}_{dork_id}"
        if cache_key in st.session_state.api_cache:
            cached_data = st.session_state.api_cache[cache_key]
            err = cached_data["error"]
            res = cached_data["results"]

            if err:
                st.error(f"❌ {err}")
            elif res:
                st.markdown("**Live Search Results:**")
                for item in res:
                    item_title = item.get("title", "No Title")
                    item_link = item.get("link", "#")
                    item_snippet = item.get("snippet", "No snippet available.")
                    
                    st.markdown(f"- **[{item_title}]({item_link})**")
                    st.caption(item_snippet)
            else:
                st.info("ℹ️ No publicly indexed search results returned for this query.")

        st.divider()

else:
    st.info("👋 Enter a username above to generate OSINT search dorks.")


# ==============================================================================
# DEPLOYMENT INSTRUCTIONS & REPOSITORY PREPARATION
# ==============================================================================
"""
--------------------------------------------------------------------------------
HOW TO DEPLOY THIS APP TO STREAMLIT COMMUNITY CLOUD (FREE):
--------------------------------------------------------------------------------

1. CREATE A 'requirements.txt' FILE:
   Save a file named `requirements.txt` in the same repository containing:
   
   streamlit>=1.30.0
   requests>=2.31.0

2. GOOGLE CUSTOM SEARCH CREDENTIALS (OPTIONAL):
   - Get API Key: Go to Google Cloud Console -> APIs & Services -> Credentials.
     Enable "Custom Search API".
   - Get CX ID: Go to https://programmablesearchengine.google.com/ -> Create Engine.
     Set "Search the entire web" to ON. Copy the Search Engine ID (CX).

3. CONFIGURE SECRETS (STREAMLIT COMMUNITY CLOUD):
   Instead of typing credentials manually each session, add secrets in Streamlit Cloud:
   
   [GOOGLE_API_KEY]
   GOOGLE_API_KEY = "your_actual_api_key_here"
   GOOGLE_CX = "your_actual_cx_id_here"

4. DEPLOYMENT STEPS:
   - Push `app.py` and `requirements.txt` to a public GitHub repository.
   - Go to https://share.streamlit.io/
   - Connect your GitHub account and click "New app".
   - Select your repository, branch (main), and main file path (`app.py`).
   - Click "Deploy!".
--------------------------------------------------------------------------------
"""

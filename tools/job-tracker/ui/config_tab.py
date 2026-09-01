import streamlit as st
import yaml
from config import CONFIG_PATH


def _load():
    try:
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}


def _save(cfg):
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def render_config():
    st.markdown("### [config]")

    cfg = _load()

    col_key, col_model = st.columns(2)
    with col_key:
        st.text_input("OpenRouter API Key", key="cfg_api_key",
                      value=cfg.get("openrouter_api_key", ""), type="password")
    with col_model:
        st.text_input("Model", key="cfg_model",
                      value=cfg.get("openrouter_model", "google/gemini-2.5-flash"))

    st.markdown("#### Gmail Accounts")
    st.html('<p style="font-family:JetBrains Mono,monospace; font-size:11px; color:#aaa; margin-bottom:8px;">'
            'Use Gmail app-specific passwords (not your main password).</p>')

    existing = cfg.get("gmail_accounts") or []
    if "cfg_n_accounts" not in st.session_state:
        st.session_state["cfg_n_accounts"] = max(1, len(existing))
        for i, acc in enumerate(existing):
            st.session_state[f"cfg_addr_{i}"] = acc.get("address", "")
            st.session_state[f"cfg_pwd_{i}"] = acc.get("app_password", "")

    n = st.session_state["cfg_n_accounts"]

    for i in range(n):
        c1, c2, c3 = st.columns([5, 5, 1])
        with c1:
            st.text_input(f"Address {i + 1}", key=f"cfg_addr_{i}")
        with c2:
            st.text_input(f"App password {i + 1}", key=f"cfg_pwd_{i}", type="password")
        with c3:
            st.markdown("<br>", unsafe_allow_html=True)
            if n > 1 and st.button("[x]", key=f"cfg_rm_{i}"):
                for j in range(i, n - 1):
                    st.session_state[f"cfg_addr_{j}"] = st.session_state.get(f"cfg_addr_{j + 1}", "")
                    st.session_state[f"cfg_pwd_{j}"] = st.session_state.get(f"cfg_pwd_{j + 1}", "")
                st.session_state["cfg_n_accounts"] = n - 1
                st.rerun()

    if st.button("[+] Add account"):
        st.session_state["cfg_n_accounts"] = n + 1
        st.rerun()

    st.divider()

    if st.button("[save] Save config", type="primary"):
        accounts = []
        for i in range(st.session_state["cfg_n_accounts"]):
            addr = st.session_state.get(f"cfg_addr_{i}", "").strip()
            pwd = st.session_state.get(f"cfg_pwd_{i}", "").strip()
            if addr:
                accounts.append({"address": addr, "app_password": pwd})

        cfg["openrouter_api_key"] = st.session_state.get("cfg_api_key", "").strip()
        cfg["openrouter_model"] = (st.session_state.get("cfg_model") or "google/gemini-2.5-flash").strip()
        cfg["gmail_accounts"] = accounts
        _save(cfg)
        st.session_state.pop("cfg_n_accounts", None)
        st.cache_data.clear()
        st.success("[ok] Config saved — restart to apply")

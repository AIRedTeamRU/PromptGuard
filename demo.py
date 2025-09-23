# demo.py
import streamlit as st
import requests

st.title("🛡️ PromptGuard Demo")
prompt = st.text_area("Введите промпт:")

if st.button("Проверить"):
    response = requests.post(
        "https://promptguard.onrender.com/v1/guard-prompt",
        json={"prompt": prompt}
    )
    result = response.json()
    if result["is_safe"]:
        st.success("✅ Безопасно!")
    else:
        st.error("🚨 Заблокировано!")
        st.write(result["suggested_rewrite"])
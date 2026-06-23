import streamlit as st
from google import genai
from google.genai import types
import json
from pydantic import BaseModel
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="AI CRM Reconciler", layout="wide")
st.title("⚡ AI Catalyst: CRM Data Reconciler")
st.markdown("Transform messy sales call transcripts into structured CRM records and automated follow-ups instantly.")

# Configure the modern Gemini Client securely via Streamlit secrets
try:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
except KeyError:
    st.error("Missing API Key. Please add it to .streamlit/secrets.toml")
    st.stop()

# --- 2. DEFINE THE STRICT DATA SCHEMA ---
class CRMRecord(BaseModel):
    company_name: str
    deal_size_estimate: str
    budget_identified: bool
    decision_maker_present: bool
    core_pain_points: list[str]
    competitors_mentioned: list[str]
    next_steps_action_items: list[str]
    deal_confidence_score: int # 1 to 100

# --- 3. UI LAYOUT ---
col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("📥 Data Ingestion")
    
    # Input options: Paste or Upload
    upload_method = st.radio("Input Method:", ["Paste Text", "Upload File (.txt)"], horizontal=True)
    
    transcript_input = ""
    if upload_method == "Paste Text":
        transcript_input = st.text_area(
            "Paste Zoom/Teams transcript here:",
            height=400,
            placeholder="e.g., 'Hey Sarah, thanks for jumping on. Let's talk about your data issues...'"
        )
    else:
        uploaded_file = st.file_uploader("Upload Zoom Transcript", type=["txt"])
        if uploaded_file is not None:
            transcript_input = uploaded_file.getvalue().decode("utf-8")
            st.success("Transcript loaded successfully!")
            
    analyze_btn = st.button("Process to CRM 🚀", type="primary", use_container_width=True)

with col2:
    st.subheader("📊 Executive Dashboard")
    
    if analyze_btn and transcript_input:
        with st.spinner("Analyzing BANT (Budget, Authority, Need, Timeline)..."):
            try:
                # --- 4. THE AI ENGINE CALL ---
                prompt = f"You are a RevOps data extraction agent. Extract the required CRM fields from this raw sales transcript: {transcript_input}"
                
                # Enforcing the JSON schema
                response = client.models.generate_content(
                    model='gemini-3-flash-preview',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=CRMRecord,
                    )
                )
                
                # Parse the guaranteed JSON
                crm_data = json.loads(response.text)
                
                # --- 5. TOP-LEVEL KPI METRICS ---
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Confidence Score", f"{crm_data['deal_confidence_score']}/100")
                m2.metric("Deal Size", crm_data['deal_size_estimate'])
                m3.metric("Budget Verified", "✅ Yes" if crm_data['budget_identified'] else "❌ No")
                m4.metric("Authority (DM)", "✅ Yes" if crm_data['decision_maker_present'] else "❌ No")
                
                st.divider()
                
                # --- 6. DATA VISUALIZATIONS ---
                chart_col1, chart_col2 = st.columns(2)
                
                with chart_col1:
                    # Metric A: Deal Confidence Gauge
                    fig_gauge = go.Figure(go.Indicator(
                        mode="gauge+number",
                        value=crm_data['deal_confidence_score'],
                        title={'text': "Deal Health / Confidence"},
                        gauge={
                            'axis': {'range': [0, 100]},
                            'bar': {'color': "rgba(0,0,0,0)"},  # Hidden default indicator bar
                            'steps': [
                                {'range': [0, 40], 'color': "#ff4b4b"},    # Red Zone
                                {'range': [40, 75], 'color': "#ffa421"},   # Yellow Zone
                                {'range': [75, 100], 'color': "#21c354"}   # Green Zone
                            ],
                            'threshold': {
                                'line': {'color': "black", 'width': 4},
                                'thickness': 0.75,
                                'value': crm_data['deal_confidence_score']
                            }
                        }
                    ))
                    fig_gauge.update_layout(height=280, margin=dict(l=20, r=20, t=40, b=20))
                    st.plotly_chart(fig_gauge, use_container_width=True)

                with chart_col2:
                    # Metric B: Strategic BANT Radar Alignment
                    budget_val = 100 if crm_data['budget_identified'] else 20
                    auth_val = 100 if crm_data['decision_maker_present'] else 20
                    need_val = min(100, len(crm_data['core_pain_points']) * 35)
                    timeline_val = min(100, len(crm_data['next_steps_action_items']) * 40)

                    df_radar = pd.DataFrame(dict(
                        r=[budget_val, auth_val, need_val, timeline_val],
                        theta=['Budget', 'Authority', 'Need', 'Timeline']
                    ))
                    fig_radar = px.line_polar(df_radar, r='r', theta='theta', line_close=True)
                    fig_radar.update_traces(fill='toself', fillcolor='rgba(33, 195, 84, 0.3)', line_color='#21c354')
                    fig_radar.update_layout(
                        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                        showlegend=False,
                        height=280,
                        margin=dict(l=40, r=40, t=40, b=40)
                    )
                    st.plotly_chart(fig_radar, use_container_width=True)
                
                st.divider()
                
                # --- 7. DETAILED EXTRACTED DATA ---
                st.markdown(f"**Target Account:** {crm_data['company_name']}")
                
                st.markdown("**Core Pain Points (Need):**")
                for pain in crm_data['core_pain_points']:
                    st.markdown(f"- 🔴 {pain}")
                    
                st.markdown("**Competitors Mentioned:**")
                if crm_data['competitors_mentioned']:
                    for comp in crm_data['competitors_mentioned']:
                        st.markdown(f"- ⚔️ {comp}")
                else:
                    st.markdown("- *None explicitly mentioned.*")
                    
                st.markdown("**Next Steps (Timeline):**")
                for step in crm_data['next_steps_action_items']:
                    st.markdown(f"- 📆 {step}")
                
                st.divider()
                
                # --- 8. ACTION ENGINE: AUTO-DRAFTED FOLLOW-UP ---
                st.markdown("### ✉️ Action Engine: Follow-Up Draft")
                with st.expander("View AI-Generated Follow-Up Email", expanded=True):
                    primary_pain = crm_data['core_pain_points'][0] if crm_data['core_pain_points'] else 'improving your current workflow'
                    primary_next_step = crm_data['next_steps_action_items'][0] if crm_data['next_steps_action_items'] else 'reconnect next week'
                    
                    email_draft = f"Hi Team,\n\nGreat speaking today. To recap, I understand your main priority is {primary_pain}.\n\nAs discussed, our next step is to {primary_next_step}. Let me know if anything changes on your end.\n\nBest,\nSales Team"
                    st.text_area("Copy to Gmail/Outlook:", value=email_draft, height=180)

                st.divider()

                # --- 9. EXPORT DATA ---
                st.markdown("### 💾 Export Data")
                json_string = json.dumps(crm_data, indent=2)
                st.download_button(
                    label="Download as JSON (Ready for API Integration)",
                    file_name=f"{crm_data['company_name'].replace(' ', '_')}_CRM_Payload.json",
                    data=json_string,
                    mime="application/json",
                    type="primary"
                )
                
                st.success("Workflow Complete.")
                
            except Exception as e:
                st.error(f"An error occurred: {e}")
    elif analyze_btn and not transcript_input:
        st.warning("Please provide a transcript first.")
    else:
        st.info("Awaiting raw transcript input. Paste text or upload a file on the left to begin.")
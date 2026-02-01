# app.py
import streamlit as st
from workflow import DisasterResponseAgent
import os
from datetime import datetime
from PIL import Image

# Page config
st.set_page_config(
    page_title="Disaster Response AI",
    page_icon="🚨",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        color: #FF4B4B;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
    }
    .stAlert {
        margin-top: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.markdown('<p class="main-header">🚨 Disaster Response AI Agent</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Upload an image of a disaster to receive instant risk assessment and action plans</p>', unsafe_allow_html=True)

# Initialize agent (with caching to avoid rebuilding)
@st.cache_resource
def load_agent():
    return DisasterResponseAgent()

agent = load_agent()

# Create two columns for layout
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📤 Upload Disaster Image")
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Choose an image...",
        type=["jpg", "jpeg", "png"],
        help="Upload an image of a disaster scene for analysis"
    )
    
    if uploaded_file is not None:
        # Display the uploaded image
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Image", use_container_width=True)
        
        # Save the image temporarily
        image_path = f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpeg"
        image.save(image_path)
        
        # Analyze button
        if st.button("🔍 Analyze Disaster", type="primary", use_container_width=True):
            with st.spinner("🤖 AI Agent is analyzing the disaster..."):
                try:
                    # Run the agent
                    result = agent.workflow.invoke({
                        "image_path": image_path
                    })
                    
                    # Store result in session state
                    st.session_state['result'] = result
                    st.session_state['image_path'] = image_path
                    
                    st.success("✅ Analysis complete!")
                    
                except Exception as e:
                    st.error(f"❌ Error during analysis: {str(e)}")
                    # Clean up temp file
                    if os.path.exists(image_path):
                        os.remove(image_path)

with col2:
    st.subheader("📊 Analysis Results")
    
    # Display results if available
    if 'result' in st.session_state:
        result = st.session_state['result']
        
        # Check if a disaster was detected
        if result['disaster']['type'].strip().lower() == 'none':
            # No disaster detected
            st.markdown("### ✅ No Disaster Detected")
            st.success("The AI analysis did not detect any wildfire or flood in the uploaded image.")
            st.info(f"**Analysis:** {result['disaster']['description']}")
            
            # Clear analysis button
            if st.button("🗑️ Clear Analysis", use_container_width=True):
                if 'image_path' in st.session_state and os.path.exists(st.session_state['image_path']):
                    os.remove(st.session_state['image_path'])
                del st.session_state['result']
                del st.session_state['image_path']
                st.rerun()
        
        else:
            # Disaster detected - show full analysis
            # Disaster Detection Section
            st.markdown("### 🎯 Disaster Detection")
            st.info(f"**Type:** {result['disaster']['type']}")
            st.write(f"**Description:** {result['disaster']['description']}")
            
            st.markdown("---")
            
            # Risk Assessment Section
            st.markdown("### ⚠️ Risk Assessment")
            
            # Color-code based on severity
            risk_level = result['risk_level'].lower()
            if 'high' in risk_level or 'severe' in risk_level or 'critical' in risk_level:
                st.error(result['risk_level'])
            elif 'medium' in risk_level or 'moderate' in risk_level:
                st.warning(result['risk_level'])
            else:
                st.success(result['risk_level'])
            
            st.markdown("---")
            
            # Action Plan Section
            st.markdown("### 📋 Action Plan")
            st.markdown(result['action_plan'])
            
            # Download button for the report
            st.markdown("---")
            report = f"""
# Disaster Response Report

## Disaster Detection
- **Type:** {result['disaster']['type']}
- **Description:** {result['disaster']['description']}

## Risk Assessment
{result['risk_level']}

## Action Plan
{result['action_plan']}

---
*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
            
            st.download_button(
                label="📥 Download Report",
                data=report,
                file_name=f"disaster_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                mime="text/markdown",
                use_container_width=True
            )
            
            # Clean up button
            if st.button("🗑️ Clear Analysis", use_container_width=True):
                # Remove temp file
                if 'image_path' in st.session_state and os.path.exists(st.session_state['image_path']):
                    os.remove(st.session_state['image_path'])
                # Clear session state
                del st.session_state['result']
                del st.session_state['image_path']
                st.rerun()
    
    else:
        st.info("👆 Upload an image and click 'Analyze Disaster' to see results here")

# Footer
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: #666;'>Powered by LangGraph & Groq AI | "
    "Built for SanD Hacks</p>",
    unsafe_allow_html=True
)


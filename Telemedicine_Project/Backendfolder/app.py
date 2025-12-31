import streamlit as st
import joblib
import pandas as pd
import re
import plotly.graph_objects as go
from PIL import Image
import io
import base64
import requests
import json
import google.generativeai as genai
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os.path
import pickle
from datetime import datetime, timedelta

# Set page configuration
st.set_page_config(
    page_title="Medical Analysis Suite",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Keys
# API Keys for Injury Analysis
GEMINI_API_KEY = "your API key"
GOOGLE_SEARCH_API_KEY = "your API key"
GOOGLE_CX = "your API key"


# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Google Calendar API setup
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Custom CSS
st.markdown("""
    <style>
        .main { background-color: #f8f9fa; }
        .stButton>button {
            background-color: #007bff;
            color: white;
            border-radius: 50px;
            padding: 0.5rem 2rem;
            border: none;
        }
        .stButton>button:hover { background-color: #0056b3; }
        .severity-box {
            padding: 20px;
            border-radius: 15px;
            margin: 10px 0;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .high-severity { background-color: black; border-left: 5px solid #ff4444; }
        .moderate-severity { background-color: black; border-left: 5px solid #ffa500; }
        .low-severity { background-color: black; border-left: 5px solid #44ff44; }
        .stTextArea>div>div {
            background-color: black;
            border-radius: 10px;
            border: 1px solid #e0e0e0;
        }
        .upload-box {
            border: 2px dashed #007bff;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            margin: 20px 0;
        }
        .metric-card {
            background-color: black;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        .appointment-card {
            background-color:black;
            padding: 20px;
            border-radius: 10px;
            margin: 10px 0;
            border-left: 4px solid #007bff;
        }
    </style>
""", unsafe_allow_html=True)

# Helper Functions
def analyze_duration_context(text):
    text_lower = text.lower()
    duration_indicators = {
        'days': r'(\d+)\s*days?',
        'weeks': r'(\d+)\s*weeks?',
        'months': r'(\d+)\s*months?'
    }

    additional_context = []

    for period, pattern in duration_indicators.items():
        matches = re.findall(pattern, text_lower)
        if matches:
            duration = int(matches[0])
            if period == 'days' and duration > 7:
                additional_context.append(f"⚠️ Symptoms persisting for {duration} days may require medical evaluation.")
            elif period == 'weeks' and duration > 1:
                additional_context.append(f"⚠️ Symptoms persisting for {duration} weeks require medical attention.")
            elif period == 'months':
                additional_context.append(f"⚠️ Chronic condition lasting {duration} months - medical evaluation recommended.")

    symptoms_of_concern = {
        'fever': "Monitor temperature and stay hydrated",
        'chest pain': "Seek immediate medical attention for chest pain",
        'difficulty breathing': "Monitor oxygen levels and breathing pattern",
        'shortness of breath': "Monitor oxygen levels and breathing pattern",
        'cold': "Monitor symptoms and seek medical attention if persisting beyond a week",
        'cough': "Monitor cough progression and any changes in character",
        'headache': "Monitor intensity and frequency of headaches",
        'pain': "Track pain levels and any changes in intensity or location"
    }

    for symptom, advice in symptoms_of_concern.items():
        if symptom in text_lower:
            additional_context.append(f"🔔 {advice}")

    return additional_context

def create_gauge_chart(value, title, severity):
    colors = {'High': 'red', 'Moderate': 'orange', 'Low': 'green'}

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value * 100,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title, 'font': {'size': 24}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1},
            'bar': {'color': colors.get(severity, 'blue')},
            'bgcolor': "white",
            'steps': [
                {'range': [0, 33], 'color': "rgba(255, 0, 0, 0.1)"},
                {'range': [33, 66], 'color': "rgba(255, 165, 0, 0.1)"},
                {'range': [66, 100], 'color': "rgba(0, 255, 0, 0.1)"}
            ],
            'threshold': {
                'line': {'color': colors.get(severity, 'blue'), 'width': 4},
                'thickness': 0.75,
                'value': value * 100
            }
        }
    ))

    fig.update_layout(height=250, font={'size': 16}, margin=dict(l=20, r=20, t=40, b=20))
    return fig

# Calendar Functions
from google.oauth2 import service_account

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

def send_appointment_email(patient_email, doctor, date, time, symptoms):
   sender_email = "gandhamsaketh073@gmail.com"  
   sender_password = "oyad zwxr txuv wpgi"
   doctor_emails = {
       "Dr. Smith - Cardiologist": "gandhamsaketh073@gmail.com",
       "Dr. Johnson - General Physician": "gandhamsaketh073@gmail.com",
       "Dr. Williams - Pediatrician": "gandhamsaketh073@gmail.com",
       "Dr. Brown - Dermatologist": "gandhamsaketh073@gmail.com"
   }

   appointment_time = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
   calendar_html = f"""<a href="https://calendar.google.com/calendar/render?action=TEMPLATE&text=Medical+Appointment&dates={appointment_time.strftime('%Y%m%dT%H%M%S')}/{(appointment_time + timedelta(minutes=30)).strftime('%Y%m%dT%H%M%S')}&details=Doctor:+{doctor}%0ASymptoms:+{symptoms}&location=Medical+Center" 
          style="background: #28a745; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 15px;">Add to Calendar</a>"""

   patient_msg = MIMEMultipart('alternative')
   doctor_msg = MIMEMultipart('alternative')
   
   patient_msg['Subject'] = 'Medical Appointment Confirmation'
   patient_msg['From'] = sender_email
   patient_msg['To'] = patient_email
   
   doctor_msg['Subject'] = f'New Patient Appointment'
   doctor_msg['From'] = sender_email
   doctor_msg['To'] = doctor_emails[doctor]
   
   email_style = """
       body { font-family: Arial; }
       .header { background: linear-gradient(135deg, #0056b3, #007bff); color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }
       .content { padding: 20px; border: 1px solid #ddd; border-radius: 0 0 10px 10px; }
       .details { background: #f8f9fa; padding: 15px; margin: 10px 0; border-left: 4px solid #007bff; border-radius: 5px; }
   """
   
   patient_html = MIMEText(f"""
   <html><head><style>{email_style}</style></head>
   <body>
       <div class="header"><h1>🏥 Appointment Confirmation</h1></div>
       <div class="content">
           <div class="details">
               <p><strong>Doctor:</strong> {doctor}</p>
               <p><strong>Date:</strong> {appointment_time.strftime('%B %d, %Y')}</p>
               <p><strong>Time:</strong> {appointment_time.strftime('%I:%M %p')}</p>
               <p><strong>Symptoms:</strong> {symptoms}</p>
           </div>
           {calendar_html}
       </div>
   </body></html>
   """, 'html')
   
   doctor_html = MIMEText(f"""
   <html><head><style>{email_style}</style></head>
   <body>
       <div class="header"><h1>🏥 New Patient Appointment</h1></div>
       <div class="content">
           <div class="details">
               <p><strong>Patient:</strong> {patient_email}</p>
               <p><strong>Date:</strong> {appointment_time.strftime('%B %d, %Y')}</p>
               <p><strong>Time:</strong> {appointment_time.strftime('%I:%M %p')}</p>
               <p><strong>Symptoms:</strong> {symptoms}</p>
           </div>
           {calendar_html}
       </div>
   </body></html>
   """, 'html')

   patient_msg.attach(patient_html)
   doctor_msg.attach(doctor_html)

   try:
       with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
           server.login(sender_email, sender_password)
           server.send_message(patient_msg)
           server.send_message(doctor_msg)
       return True
   except Exception as e:
       print(f"Email error: {e}")
       return False

def get_google_calendar_service():
    creds = None
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
            
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=8501)  # Changed to 8501
            
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    return build('calendar', 'v3', credentials=creds)

def create_appointment(service, patient_name, date, time, doctor, symptoms):
    try:
        start_time = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        end_time = start_time + timedelta(minutes=30)
        
        event = {
            'summary': f'Medical Appointment - {patient_name}',
            'description': f'Patient: {patient_name}\nSymptoms: {symptoms}\nDoctor: {doctor}',
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'UTC',
            },
            'attendees': [
                {'email': 'gandhamsaketh073@gmail.com'}  # Add your email here
            ]
        }
        
        result = service.events().insert(calendarId='primary', sendUpdates='all', body=event).execute()
        return result
    except Exception as e:
        print(f"Error creating appointment: {str(e)}")
        raise e

def display_appointments(service):
    now = datetime.utcnow().isoformat() + 'Z'
    events_result = service.events().list(
        calendarId='primary',
        timeMin=now,
        maxResults=10,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    return events_result.get('items', [])

# Medical Text Classifier
class MedicalTextClassifier:
    def __init__(self, model_dir):
        self.model = joblib.load(f'{model_dir}/model.joblib')
        self.tfidf = joblib.load(f'{model_dir}/tfidf_vectorizer.joblib')
        self.label_encoder = joblib.load(f'{model_dir}/label_encoder.joblib')

    def preprocess_text(self, text):
        if not isinstance(text, str):
            return ''
        text = text.lower()
        text = re.sub(r'[^a-zA-Z\s.,!?]', ' ', text)
        return ' '.join(text.split())

    def predict_single(self, text):
        processed_text = self.preprocess_text(text)
        text_tfidf = self.tfidf.transform([processed_text])
        prediction_encoded = self.model.predict(text_tfidf)
        prediction_proba = self.model.predict_proba(text_tfidf)
        prediction = self.label_encoder.inverse_transform(prediction_encoded)
        class_probabilities = dict(zip(self.label_encoder.classes_, prediction_proba[0]))
        return {
            'prediction': prediction[0],
            'confidence_scores': class_probabilities,
            'processed_text': processed_text
        }

def get_medicine_images(medicine_name):
    try:
        search_url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'key': GOOGLE_SEARCH_API_KEY,
            'cx': GOOGLE_CX,
            'q': f"{medicine_name} medicine product",
            'searchType': 'image',
            'num': 1,
            'imgSize': 'MEDIUM'
        }
        response = requests.get(search_url, params=params)
        results = response.json()

        if 'items' in results:
            return results['items'][0]['link']
        return None
    except Exception as e:
        st.error(f"Error fetching image: {str(e)}")
        return None

def analyze_injury(image_data):
    prompt = """
    Analyze this injury image and provide a CONCISE emergency response in the following format:

    INJURY TYPE:
    [Brief one-line description of injury type]

    SEVERITY:
    [Simple rating: Minor, Moderate, or Severe]

    IMMEDIATE ACTIONS:
    1. [First step]
    2. [Second step]
    3. [Third step]

    REQUIRED ITEMS:
    - [Specific medicine/item 1 with exact product name]
    - [Specific medicine/item 2 with exact product name]
    - [Specific medicine/item 3 with exact product name]

    SEEK MEDICAL HELP IF:
    • [Critical condition 1]
    • [Critical condition 2]
    """

    try:
        image_bytes = io.BytesIO()
        image_data.save(image_bytes, format='PNG')
        image_bytes = image_bytes.getvalue()

        vision_data = {'mime_type': 'image/png', 'data': image_bytes}
        response = model.generate_content([prompt, vision_data])
        analysis_text = response.text

        medicine_section = [section for section in analysis_text.split('\n\n') if 'REQUIRED ITEMS:' in section][0]
        medicine_items = [item.replace('-', '').strip() for item in medicine_section.split('\n')[1:]]

        medicine_images = {}
        for medicine in medicine_items:
            image_url = get_medicine_images(medicine)
            if image_url:
                medicine_images[medicine] = image_url

        return {'analysis': analysis_text, 'medicine_images': medicine_images}
    except Exception as e:
        return {'error': str(e)}

def appointment_section():
    st.title("📅 Appointment Booking")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🗓️ Book New Appointment")
        with st.form("appointment_form"):
            patient_name = st.text_input("Patient Name")
            patient_email = st.text_input("Patient Email")
            date = st.date_input("Date")
            time = st.time_input("Time")
            doctor = st.selectbox(
                "Select Doctor",
                ["Dr. Smith - Cardiologist", "Dr. Johnson - General Physician",
                 "Dr. Williams - Pediatrician", "Dr. Brown - Dermatologist"]
            )
            symptoms = st.text_area("Symptoms/Reason for Visit")
            
            submit = st.form_submit_button("Book Appointment")
            
            if submit and patient_name and patient_email and symptoms:
                if send_appointment_email(patient_email, doctor, date.strftime("%Y-%m-%d"), 
                                       time.strftime("%H:%M"), symptoms):
                    st.success("✅ Appointment booked successfully! Check your email for confirmation and calendar invite.")
                else:
                    st.error("Error sending confirmation email")
    
    with col2:
        st.markdown("### 📋 Appointment Details")
        if 'appointments' not in st.session_state:
            st.session_state.appointments = []
            
        if submit and patient_name and patient_email:
            new_appointment = {
                'patient': patient_name,
                'doctor': doctor,
                'date': date,
                'time': time,
                'symptoms': symptoms
            }
            st.session_state.appointments.append(new_appointment)
            
        if st.session_state.appointments:
            for appt in st.session_state.appointments:
                with st.container():
                    st.markdown(
                        f"""
                        <div class='appointment-card'>
                            <h4>Patient: {appt['patient']}</h4>
                            <p>🕒 {appt['date'].strftime('%B %d, %Y')} at {appt['time'].strftime('%I:%M %p')}</p>
                            <p>Doctor: {appt['doctor']}</p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
        else:
            st.info("No upcoming appointments")

def main():
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/000000/caduceus.png", width=100)
        st.title("MediScan")
        st.markdown("---")

        selected_feature = st.radio(
            "Choose Feature",
            ["Medical Text Analysis", "Injury Analysis", "Appointment Booking"]
        )

        st.markdown("""
          ### About
          MediScan uses advanced AI to analyze medical text and assess severity levels. Perfect for:
          - Emergency triage
          - Patient monitoring
          - Clinical documentation
          - Appointment scheduling
          """)
        st.markdown("---")
        st.markdown("""
          <div style='position: fixed; bottom: 0; left: 0; padding: 10px; width: 100%; text-align: center; background-color: black;'>
              <p style='margin: 0;'>Made with ❤️ by Group-1<br>Lead by <b>Gandham Mani Saketh</b></p>
          </div>
          """, unsafe_allow_html=True)
        # Main content based on selected feature
    if selected_feature == "Medical Text Analysis":
        st.title("MediScan - Medical Text Analysis")

        try:
            classifier = MedicalTextClassifier('/content/models/medical_classifier_20250126_185815')
            st.success("✅ AI Model Ready", icon="✨")

            tab1, tab2 = st.tabs(["📝 Single Case Analysis", "📊 Bulk Case Analysis"])

            example_cases = {
                "Select an example case": "",
                "Mild Cold Symptoms": """Patient presents with runny nose, mild cough, and sore throat for 2 days.
                Temperature 37.2°C. No difficulty breathing. Good appetite and energy levels.""",
                "Persistent Cold (>1 week)": """Patient reports cold symptoms persisting for 10 days including nasal congestion,
                intermittent cough, and fatigue. No fever. Some improvement noted but symptoms lingering. SpO2 98%, vital signs stable.""",
                "Emergency Case": """Patient presented with severe chest pain, shortness of breath, and diaphoresis.
                BP 180/100, HR 120, O2 sat 88%. ECG shows ST elevation. History of hypertension.""",
                "Moderate COVID Symptoms": """Patient presents with fever (38.5°C), persistent dry cough, fatigue, and mild
                shortness of breath for 5 days. O2 sat 94%. Some difficulty with daily activities but alert and oriented.""",
            }

            with tab1:
                st.markdown("### 🔍 Analyze Individual Medical Case")

                if 'text_input' not in st.session_state:
                    st.session_state.text_input = ""

                selected_case = st.selectbox("💡 Quick Examples", options=list(example_cases.keys()))

                text_input = st.text_area(
                    "Enter Medical Notes:",
                    value=example_cases[selected_case] if selected_case != "Select an example case" else st.session_state.text_input,
                    height=150,
                    placeholder="Type or paste medical notes here..."
                )

                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    analyze_button = st.button("🔍 Analyze Case", use_container_width=True)

                if analyze_button and text_input:
                    with st.spinner("🔄 Analyzing medical case..."):
                        result = classifier.predict_single(text_input)

                    st.markdown("### 📋 Analysis Results")
                    severity = result['prediction']
                    confidence = max(result['confidence_scores'].values())
                    context_notes = analyze_duration_context(text_input)

                    severity_class = {
                        'High': 'high-severity',
                        'Moderate': 'moderate-severity',
                        'Low': 'low-severity'
                    }.get(severity, '')

                    st.markdown(f"""
                        <div class='severity-box {severity_class}'>
                            <h2>Case Severity: {severity}</h2>
                            <p style='font-size: 1.2em;'>Confidence Level: {confidence:.1%}</p>
                        </div>
                    """, unsafe_allow_html=True)

                    if context_notes:
                        st.markdown("### 📌 Additional Considerations")
                        for note in context_notes:
                            st.markdown(f"- {note}")

                    if severity == "Low" and any("persisting" in note for note in context_notes):
                        st.warning("While current symptoms suggest low severity, the duration of symptoms indicates that medical consultation may be advisable.")

                    st.markdown("### 📊 Detailed Analysis")
                    for class_name, probability in result['confidence_scores'].items():
                        fig = create_gauge_chart(probability, f"{class_name} Severity Level", class_name)
                        st.plotly_chart(fig, use_container_width=True)

            with tab2:
                st.markdown("### 📁 Bulk Case Analysis")

                st.markdown("""
                    <div class='upload-box'>
                        <h3>📤 Upload Medical Cases</h3>
                        <p>Drag and drop your CSV file here</p>
                    </div>
                """, unsafe_allow_html=True)

                uploaded_file = st.file_uploader("", type=['csv'])

                if uploaded_file is not None:
                    try:
                        df = pd.read_csv(uploaded_file)
                        text_column = df.columns[0]

                        st.markdown("### 📋 Case Preview")
                        st.dataframe(df.head(3), use_container_width=True)

                        col1, col2, col3 = st.columns([1, 2, 1])
                        with col2:
                            if st.button("🔍 Analyze All Cases", use_container_width=True):
                                progress_bar = st.progress(0)
                                status_text = st.empty()

                                results = []
                                for i, text in enumerate(df[text_column]):
                                    result = classifier.predict_single(text)
                                    results.append(result)
                                    progress = (i + 1) / len(df)
                                    progress_bar.progress(progress)
                                    status_text.text(f"Analyzing case {i+1} of {len(df)}")

                                progress_bar.empty()
                                status_text.empty()

                                df['Severity_Level'] = [r['prediction'] for r in results]
                                df['Confidence_Score'] = [max(r['confidence_scores'].values()) for r in results]

                                st.markdown("### 📊 Analysis Summary")
                                col1, col2, col3 = st.columns(3)

                                with col1:
                                    st.markdown("""
                                        <div class='metric-card'>
                                            <h3>Total Cases</h3>
                                            <h2>{}</h2>
                                        </div>
                                    """.format(len(df)), unsafe_allow_html=True)

                                with col2:
                                    high_severity = (df['Severity_Level'] == 'High').sum()
                                    st.markdown("""
                                        <div class='metric-card'>
                                            <h3>High Severity Cases</h3>
                                            <h2 style='color: red;'>{}</h2>
                                        </div>
                                    """.format(high_severity), unsafe_allow_html=True)

                                with col3:
                                    avg_confidence = df['Confidence_Score'].mean()
                                    st.markdown("""
                                        <div class='metric-card'>
                                            <h3>Avg. Confidence</h3>
                                            <h2>{:.1%}</h2>
                                        </div>
                                    """.format(avg_confidence), unsafe_allow_html=True)

                                st.markdown("### 📋 Detailed Results")
                                st.dataframe(df, use_container_width=True)

                                csv = df.to_csv(index=False)
                                st.download_button(
                                    label="📥 Download Complete Analysis",
                                    data=csv,
                                    file_name="medical_case_analysis.csv",
                                    mime="text/csv",
                                    use_container_width=True
                                )

                                st.markdown("### 📊 Severity Distribution")
                                fig = go.Figure(data=[go.Pie(
                                    labels=df['Severity_Level'].value_counts().index,
                                    values=df['Severity_Level'].value_counts().values,
                                    hole=.3,
                                    marker_colors=['#ff4444', '#ffa500', '#44ff44']
                                )])
                                fig.update_layout(
                                    title="Distribution of Case Severities",
                                    height=400,
                                    showlegend=True
                                )
                                st.plotly_chart(fig, use_container_width=True)

                    except Exception as e:
                        st.error(f"⚠️ Error processing file: {str(e)}")

        except Exception as e:
            st.error(f"⚠️ System Error: {str(e)}")

    elif selected_feature == "Injury Analysis":
        st.title("Emergency Injury Analyzer")
        st.write("Upload an injury photo to get an emergency response, including suggested actions and required items.")

        uploaded_image = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png"])

        if uploaded_image:
            img = Image.open(uploaded_image)
            if img.mode == 'RGBA':
                img = img.convert('RGB')

            st.image(img, caption="Uploaded Image", use_column_width=True)

            if st.button("Analyze Injury"):
                st.write("Analyzing the image. Please wait...")
                result = analyze_injury(img)

                if 'error' in result:
                    st.error(f"Error: {result['error']}")
                else:
                    analysis = result['analysis']
                    medicine_images = result['medicine_images']

                    sections = analysis.split('\n\n')
                    for section in sections:
                        if "INJURY TYPE:" in section:
                            st.subheader("Injury Type")
                            st.write(section.replace("INJURY TYPE:", "").strip())
                        elif "IMMEDIATE ACTIONS:" in section:
                            st.subheader("Immediate Actions")
                            actions = section.split('\n')[1:]
                            st.write("\n".join(f"- {action.strip()}" for action in actions))
                        elif "REQUIRED ITEMS:" in section:
                            st.subheader("Required Items")
                            items = section.split('\n')[1:]
                            for item in items:
                                item_name = item.replace('-', '').strip()
                                if item_name in medicine_images:
                                    st.image(medicine_images[item_name], caption=item_name, width=150)
                                else:
                                    st.write(f"- {item_name}")
                        elif "SEEK MEDICAL HELP IF:" in section:
                            st.subheader("Seek Medical Help If")
                            warnings = section.split('\n')[1:]
                            st.write("\n".join(f"- {warning.strip()}" for warning in warnings))

    else:  # Appointment Booking
        appointment_section()

if __name__ == "__main__":
    main()





from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from models import User, Persona
from database import SessionLocal
from hashlib import sha256
from typing import Optional, Union
from transformers import pipeline

app = FastAPI()

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

sentiment_pipeline = pipeline("sentiment-analysis")

# DB session dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Request models
class UserAuth(BaseModel):
    email: str
    password: str

class PersonaCreate(BaseModel):
    email: str
    name: str
    business_type: str
    customer_id: Optional[str] = None

class AnalysisRequest(BaseModel):
    business_type: str
    customer_id: Union[str, int]
    message: str

# 🔐 SIGN UP
@app.post("/signup")
def signup(user: UserAuth, db: Session = Depends(get_db)):
    existing = db.query(User).filter_by(email=user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = sha256(user.password.encode()).hexdigest()
    new_user = User(email=user.email, hashed_password=hashed)
    db.add(new_user)
    db.commit()
    return {"message": "Signup successful"}

# 🔐 LOGIN
@app.post("/login")
def login(user: UserAuth, db: Session = Depends(get_db)):
    found = db.query(User).filter_by(email=user.email).first()
    if not found or found.hashed_password != sha256(user.password.encode()).hexdigest():
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"message": "Login successful"}

# 🧠 GET PERSONAS
@app.get("/get_personas")
def get_personas(email: str, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return [
        {
            "name": p.name,
            "business_type": p.business_type,
            "customer_id": p.customer_id,
        }
        for p in user.personas
    ]

# ➕ ADD PERSONA
@app.post("/add_persona")
def add_persona(data: PersonaCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=data.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_persona = Persona(
        name=data.name,
        business_type=data.business_type,
        customer_id=data.customer_id or str(int(__import__('time').time() * 1000)),
        user_id=user.id
    )
    db.add(new_persona)
    db.commit()
    return {
        "message": "Persona added",
        "persona": {
            "name": new_persona.name,
            "business_type": new_persona.business_type,
            "customer_id": new_persona.customer_id
        }
    }

# 🤖 ANALYZE
@app.post("/analyze")
def analyze(req: AnalysisRequest):
    history = []  # You can expand this later
    business_response = "Thank you for your message. We're looking into it."

    sentiment = analyze_sentiment(req.message)
    comm_quality = evaluate_communication(req.message, business_response, req.business_type, history)
    journey = analyze_journey(req.business_type, str(req.customer_id), history + [{
        "customer_message": req.message,
        "business_response": business_response,
        "sentiment": sentiment,
        "feedback": comm_quality
    }])
    return {
        "sentiment_analysis": sentiment,
        "communication_quality": comm_quality,
        "customer_journey": journey,
        "business_response": business_response
    }

# AI UTILITIES
def analyze_sentiment(msg):
    result = sentiment_pipeline(msg)[0]
    return f"{result['label']} (confidence: {round(result['score'] * 100)}%)"

def evaluate_communication(msg, resp, business_type, history):
    return f"""
Score: 7/10
Clarity: 8/10
Empathy: 6/10
Relevance: 7/10
Improvement Suggestions:
- Acknowledge user's concern.
- Use more empathetic tone.
- Offer clearer next steps.
"""

def analyze_journey(btype, cid, hist):
    return f"Customer shows consistent interest in {btype.lower()} topics.\nTone is mostly neutral to positive.\nThey respond quickly and stay engaged.\n\nSuggestion:\nEncourage further engagement by offering tailored responses or follow-up questions."

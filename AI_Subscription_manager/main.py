import os
import smtplib
import models
import database
from email.message import EmailMessage
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from jose import jwt, JWTError
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

# Import local modules
from auth import hash_password, verify_password, create_access_token
from agent import graph
from langchain_core.messages import HumanMessage

# ---------------- CONFIG ---------------- #
load_dotenv()
EMAIL_ADDRESS = os.getenv("EMAIL_USER") 
EMAIL_PASSWORD = os.getenv("EMAIL_PASS")
SECRET_KEY = "mysecretkey" #

# ---------------- APP & SCHEDULER ---------------- #
app = FastAPI(title="AI Subscription Manager")
scheduler = BackgroundScheduler()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

database.init_db()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# ---------------- AUTH ---------------- #
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = db.query(models.User).filter(models.User.id == user_id).first()
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ---------------- SCHEMAS ---------------- #
class UserCreate(BaseModel):
    email: str
    full_name: str
    password: str

class SubscriptionRequest(BaseModel):
    tool_name: str
    cost: float
    billing_cycle: str
    purchase_date: date
    renewal_date: date = None

class ChatRequest(BaseModel):
    query: str

# ---------------- EMAIL LOGIC ---------------- #
def send_email_notification(to_email, tool_name, r_date, cost):
    msg = EmailMessage()
    msg.set_content(
        f"Hi there,\n\n"
        f"This is an automated alert from your AI Subscription Manager.\n"
        f"Your subscription for '{tool_name}' is renewing in 2 days on {r_date}.\n"
        f"Expected Cost: ${cost}\n\n"
        f"Please ensure your payment method is up to date."
    )
    msg['Subject'] = f"🔔 Renewal Alert: {tool_name}"
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = to_email

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
            smtp.starttls() 
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
            print(f"SUCCESS: Alert sent to {to_email} for {tool_name}")
    except Exception as e:
        print(f"FAILED to send email: {e}")

# ---------------- SCHEDULER TASK ---------------- #
def check_for_upcoming_renewals():
    print(f"DEBUG: Running renewal check at {datetime.now()}")
    db = database.SessionLocal()
    try:
        target_date = date.today() + timedelta(days=2)

        upcoming = db.query(models.Subscription).filter(
            models.Subscription.renewal_date == target_date
        ).all()
        
        print(f"DEBUG: Found {len(upcoming)} subscriptions renewing on {target_date}")

        for sub in upcoming:
            user = db.query(models.User).filter(models.User.id == sub.user_id).first()
            if user and EMAIL_ADDRESS:
                send_email_notification(user.email, sub.tool_name, sub.renewal_date, sub.cost)
            else:
                print(f"LOG: Skipping {sub.tool_name}. Reason: User found={bool(user)}, Email config={bool(EMAIL_ADDRESS)}")
    except Exception as e:
        print(f"SCHEDULER ERROR: {e}")
    finally:
        db.close()

@app.on_event("startup")
def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(
            check_for_upcoming_renewals, 
            'interval', 
            hours=24, 
            next_run_time=datetime.now()
        )
        scheduler.start()
        print("INFO: Background Scheduler Started")

# ---------------- ENDPOINTS ---------------- #
@app.get("/")
def home():
    return {"status": "AI Subscription Manager Active", "sender_configured": bool(EMAIL_ADDRESS)}

@app.post("/signup/")
def signup(user: UserCreate, db: Session = Depends(database.get_db)):
    new_user = models.User(email=user.email, full_name=user.full_name, password=hash_password(user.password))
    db.add(new_user)
    db.commit()
    return {"message": "User created"}

@app.post("/login/")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"access_token": create_access_token({"user_id": user.id}), "token_type": "bearer"}

@app.post("/subscriptions/")
def create_subscription(request: SubscriptionRequest, current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    p_date = request.purchase_date
    if request.renewal_date:
        r_date = request.renewal_date
    else:
        days = {"weekly": 7, "monthly": 30, "yearly": 365}
        r_date = p_date + timedelta(days=days.get(request.billing_cycle.lower(), 30))

    new_sub = models.Subscription(
        tool_name=request.tool_name, cost=request.cost, billing_cycle=request.billing_cycle,
        purchase_date=p_date, renewal_date=r_date, user_id=current_user.id
    )
    db.add(new_sub)
    db.commit()
    return {"message": "Created", "data": {"tool": request.tool_name, "renewal": r_date}}

@app.get("/dashboard/")
def get_dashboard(current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    subs = db.query(models.Subscription).filter(models.Subscription.user_id == current_user.id).all()
    return {"total_spending": sum(s.cost for s in subs), "subscriptions": subs}

@app.post("/chat/")
def chat(request: ChatRequest, current_user: models.User = Depends(get_current_user)):
    config = {"configurable": {"thread_id": str(current_user.id), "user_id": current_user.id}}
    try:
        result = graph.invoke({"messages": [HumanMessage(content=request.query)]}, config=config)
        return {"response": result["messages"][-1].content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def home():
    return {"status": "AI Subscription Manager Active"}
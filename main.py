import os
from datetime import datetime, date, time, timedelta, timezone
from typing import List, Optional
from uuid import UUID, uuid4

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import (
    Column, String, DateTime, Integer, ForeignKey, Time, SmallInteger, 
    create_engine, func
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker
import pytz

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# --- DB setup -------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://user:pass@host/db")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
Base = declarative_base()

class Host(Base):
    __tablename__ = "hosts"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    slug = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    timezone = Column(String, nullable=False, default="UTC")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    availabilities = relationship("Availability", back_populates="host", cascade="all,delete")
    bookings = relationship("Booking", back_populates="host", cascade="all,delete")

class Availability(Base):
    __tablename__ = "availabilities"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    host_id = Column(PG_UUID(as_uuid=True), ForeignKey("hosts.id", ondelete="CASCADE"))
    day_of_week = Column(SmallInteger, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    slot_duration_minutes = Column(Integer, nullable=False)
    host = relationship("Host", back_populates="availabilities")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Booking(Base):
    __tablename__ = "bookings"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    host_id = Column(PG_UUID(as_uuid=True), ForeignKey("hosts.id", ondelete="CASCADE"))
    guest_name = Column(String, nullable=False)
    guest_email = Column(String, nullable=False)
    start_datetime = Column(DateTime(timezone=True), nullable=False)
    end_datetime = Column(DateTime(timezone=True), nullable=False)
    host = relationship("Host", back_populates="bookings")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# Create tables
Base.metadata.create_all(bind=engine)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- Pydantic schemas -----------------------------------------
class HostCreate(BaseModel):
    name: str
    email: EmailStr
    timezone: str = "UTC"

class HostOut(BaseModel):
    id: UUID
    slug: str
    name: str
    email: EmailStr
    timezone: str
    class Config: 
        from_attributes = True

class AvailabilityCreate(BaseModel):
    day_of_week: int = Field(..., ge=0, le=6)
    start_time: time
    end_time: time
    slot_duration_minutes: int = Field(..., ge=15, le=60)

class AvailabilityOut(BaseModel):
    id: UUID
    day_of_week: int
    start_time: time
    end_time: time
    slot_duration_minutes: int
    class Config: 
        from_attributes = True

class BookingCreate(BaseModel):
    guest_name: str
    guest_email: EmailStr
    start_datetime: datetime

class BookingOut(BaseModel):
    id: UUID
    guest_name: str
    guest_email: EmailStr
    start_datetime: datetime
    end_datetime: datetime
    class Config: 
        from_attributes = True

# --- Dependency ------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    if token != "admin-token":
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"email": "admin@example.com"}

# --- App -------------------------------------------------------
app = FastAPI(title="Booking API", version="1.0")

# --- Auth endpoints --------------------------------------------
@app.post("/auth/login")
def login():
    return {"access_token": "admin-token", "token_type": "bearer"}

# --- Host CRUD -----------------------------------------------
@app.post("/api/v1/hosts", response_model=HostOut, status_code=201)
def create_host(host_in: HostCreate, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    slug = host_in.name.lower().replace(" ", "-")
    host = Host(**host_in.model_dump(), slug=slug)
    db.add(host)
    db.commit()
    db.refresh(host)
    return host

@app.get("/api/v1/hosts/{host_id}", response_model=HostOut)
def get_host(host_id: UUID, db: Session = Depends(get_db)):
    host = db.query(Host).filter_by(id=host_id).first()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    return host

# --- Availability -----------------------------------------------
@app.post("/api/v1/hosts/{host_id}/availabilities", response_model=AvailabilityOut, status_code=201)
def add_availability(host_id: UUID, avail_in: AvailabilityCreate, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    host = db.query(Host).filter_by(id=host_id).first()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    avail = Availability(**avail_in.model_dump(), host_id=host_id)
    db.add(avail)
    db.commit()
    db.refresh(avail)
    return avail

@app.get("/api/v1/hosts/{host_id}/availabilities", response_model=List[AvailabilityOut])
def list_availabilities(host_id: UUID, db: Session = Depends(get_db)):
    return db.query(Availability).filter_by(host_id=host_id).all()

# --- Booking creation (public) ----------------------------------
@app.post("/api/v1/hosts/{host_slug}/bookings", response_model=BookingOut, status_code=201)
def create_booking_public(host_slug: str, booking_in: BookingCreate, db: Session = Depends(get_db)):
    host = db.query(Host).filter_by(slug=host_slug).first()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    
    tz = pytz.timezone(host.timezone)
    
    # Proper UTC handling
    if booking_in.start_datetime.tzinfo is None:
        start_utc = pytz.utc.localize(booking_in.start_datetime)
    else:
        start_utc = booking_in.start_datetime.astimezone(pytz.utc)
    
    start_local = start_utc.astimezone(tz)
    end_local = start_local + timedelta(minutes=30)
    
    # Overlap check
    overlap = db.query(Booking).filter(
        Booking.host_id == host.id,
        Booking.start_datetime < end_local.astimezone(pytz.utc),
        Booking.end_datetime > start_local.astimezone(pytz.utc)
    ).first()
    
    if overlap:
        raise HTTPException(status_code=409, detail="Slot already booked")
    
    booking = Booking(
        host_id=host.id,
        guest_name=booking_in.guest_name,
        guest_email=booking_in.guest_email,
        start_datetime=start_local.astimezone(pytz.utc),
        end_datetime=end_local.astimezone(pytz.utc)
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking

# --- Public availability slots ----------------------------------
@app.get("/api/v1/hosts/{host_slug}/available-slots")
def get_available_slots(host_slug: str, start: date, end: date, db: Session = Depends(get_db)):
    host = db.query(Host).filter_by(slug=host_slug).first()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    
    slots = []
    tz = pytz.timezone(host.timezone)
    delta = timedelta(days=1)
    current = datetime.combine(start, time.min)
    
    while current.date() <= end:
        day_of_week = current.weekday()
        patterns = db.query(Availability).filter_by(host_id=host.id, day_of_week=day_of_week).all()
        
        for p in patterns:
            start_local = tz.localize(datetime.combine(current.date(), p.start_time))
            end_local = tz.localize(datetime.combine(current.date(), p.end_time))
            slot_start = start_local
            
            while slot_start + timedelta(minutes=p.slot_duration_minutes) <= end_local:
                slot_end = slot_start + timedelta(minutes=p.slot_duration_minutes)
                slots.append({
                    "start": slot_start.astimezone(pytz.utc).isoformat(),
                    "end": slot_end.astimezone(pytz.utc).isoformat()
                })s
                slot_start = slot_end
        
        current += delta
    
    # Remove booked slots
    booked = db.query(Booking).filter(
        Booking.host_id == host.id,
        Booking.start_datetime >= datetime.combine(start, time.min, tzinfo=pytz.utc),
        Booking.end_datetime <= datetime.combine(end, time.max, tzinfo=pytz.utc)
    ).all()
    
    booked_set = {(b.start_datetime.isoformat(), b.end_datetime.isoformat()) for b in booked}
    available = [s for s in slots if (s["start"], s["end"]) not in booked_set]
    
    return {"slots": available}
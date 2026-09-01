from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=True)
    phone = Column(String(30), unique=True, index=True, nullable=False)
    wallet_balance = Column(Float, default=150.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    trips = relationship("Trip", back_populates="user")

class Driver(Base):
    __tablename__ = "drivers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    avatar = Column(String(255), nullable=True)
    phone = Column(String(30), nullable=False)
    rating = Column(Float, default=4.9)
    total_trips = Column(Integer, default=0)
    vehicle_model = Column(String(100), nullable=False)
    vehicle_plate = Column(String(50), nullable=False)
    vehicle_type = Column(String(50), nullable=False)  # 'bike', 'rickshaw', 'mini', 'sedan', 'suv', etc.
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    heading = Column(Float, default=0.0)
    speed_kmh = Column(Float, default=0.0)
    is_online = Column(Boolean, default=True)
    is_busy = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    trips = relationship("Trip", back_populates="driver")

class Trip(Base):
    __tablename__ = "trips"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=True)
    
    pickup_name = Column(String(255), nullable=False)
    pickup_lat = Column(Float, nullable=False)
    pickup_lng = Column(Float, nullable=False)
    
    dropoff_name = Column(String(255), nullable=False)
    dropoff_lat = Column(Float, nullable=False)
    dropoff_lng = Column(Float, nullable=False)
    
    distance_km = Column(Float, nullable=False)
    vehicle_type = Column(String(50), nullable=False)
    mode = Column(String(50), default="indrive") # 'indrive' or 'uber'
    customer_offer = Column(Float, nullable=True)
    final_fare = Column(Float, nullable=False)
    otp = Column(String(10), nullable=False)
    status = Column(String(50), default="searching") # 'searching', 'accepted', 'arrived', 'in_progress', 'completed', 'cancelled'
    
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="trips")
    driver = relationship("Driver", back_populates="trips")

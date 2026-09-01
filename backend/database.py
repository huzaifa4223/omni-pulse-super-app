import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./omnipulse.db")

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    from models import User, Driver, Trip
    Base.metadata.create_all(bind=engine)
    
    # Auto-seed the 5 active live fleet drivers if empty
    db = SessionLocal()
    try:
        if db.query(Driver).count() == 0:
            initial_fleet = [
                Driver(
                    name="Tariq Mahmood",
                    avatar="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=200&q=80",
                    phone="+1 (555) 382-9901",
                    rating=4.96,
                    total_trips=3480,
                    vehicle_model="Toyota Corolla 2024 (Silver)",
                    vehicle_plate="NYC-7842",
                    vehicle_type="sedan",
                    lat=40.7158,
                    lng=-74.0020,
                    heading=45,
                    speed_kmh=34.0,
                    is_online=True,
                    is_busy=False
                ),
                Driver(
                    name="Alex Rivera",
                    avatar="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=200&q=80",
                    phone="+1 (555) 491-7712",
                    rating=4.91,
                    total_trips=2190,
                    vehicle_model="Honda Civic Turbo (Pearl White)",
                    vehicle_plate="BK-5521",
                    vehicle_type="sedan",
                    lat=40.7220,
                    lng=-73.9980,
                    heading=120,
                    speed_kmh=28.0,
                    is_online=True,
                    is_busy=False
                ),
                Driver(
                    name="Ahmed Bilal",
                    avatar="https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=200&q=80",
                    phone="+1 (555) 234-8899",
                    rating=4.94,
                    total_trips=2900,
                    vehicle_model="Yamaha YBR 125 (Matte Black)",
                    vehicle_plate="MOTO-409",
                    vehicle_type="bike",
                    lat=40.7100,
                    lng=-74.0110,
                    heading=270,
                    speed_kmh=42.0,
                    is_online=True,
                    is_busy=False
                ),
                Driver(
                    name="Farooq Shah",
                    avatar="https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=200&q=80",
                    phone="+1 (555) 872-1133",
                    rating=4.88,
                    total_trips=4320,
                    vehicle_model="Eco 4-Stroke CNG Auto",
                    vehicle_plate="AUT-902",
                    vehicle_type="rickshaw",
                    lat=40.7180,
                    lng=-74.0090,
                    heading=90,
                    speed_kmh=26.0,
                    is_online=True,
                    is_busy=False
                ),
                Driver(
                    name="David Chen",
                    avatar="https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?w=200&q=80",
                    phone="+1 (555) 654-3210",
                    rating=4.98,
                    total_trips=5400,
                    vehicle_model="Suzuki Swift GLX (Crimson Red)",
                    vehicle_plate="ECO-338",
                    vehicle_type="mini",
                    lat=40.7280,
                    lng=-73.9920,
                    heading=180,
                    speed_kmh=38.0,
                    is_online=True,
                    is_busy=False
                )
            ]
            db.add_all(initial_fleet)
            db.commit()
            print("[OmniPulse DB] Successfully seeded 5 initial live fleet drivers.")
    finally:
        db.close()

import math
import random
import asyncio
from datetime import datetime
from typing import List, Dict, Set
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import engine, get_db, init_db
from models import Driver, Trip, User
from schemas import (
    FareEstimateRequest,
    FareEstimateResponse,
    VehicleEstimate,
    DispatchRequest,
    DispatchResponse,
    DriverResponse,
    ModeSwitchRequest,
    ModeSwitchResponse,
    DriverBidResponse,
    TelemetryBroadcast,
    DriverTelemetryResponse,
    RideMode,
    VehicleType,
    TripStatus,
    VEHICLE_RATE_CARDS
)

# -------------------------------------------------------------
# Spatial Math Helpers (Haversine Formula)
# -------------------------------------------------------------
def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0  # Earth's mean radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)

# -------------------------------------------------------------
# WebSocket Connection Manager for Real-Time Map Streaming
# -------------------------------------------------------------
class FleetWebSocketManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast_json(self, data: dict):
        dead_connections = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception:
                dead_connections.add(connection)
        for dead in dead_connections:
            self.active_connections.discard(dead)

ws_manager = FleetWebSocketManager()

# -------------------------------------------------------------
# Background Telemetry Simulation Engine
# -------------------------------------------------------------
async def background_telemetry_stream():
    """Continuously simulates realistic live GPS coordinates and broadcasts to connected map clients."""
    while True:
        try:
            from database import SessionLocal
            db = SessionLocal()
            drivers = db.query(Driver).filter(Driver.is_online == True).all()
            
            telemetry_list = []
            for driver in drivers:
                # Add micro-drift along street coordinates
                delta_lat = (random.random() - 0.5) * 0.0008
                delta_lng = (random.random() - 0.5) * 0.0008
                driver.lat += delta_lat
                driver.lng += delta_lng
                driver.speed_kmh = round(24.0 + random.random() * 22.0, 1)
                driver.heading = (driver.heading + random.choice([-15, 0, 15]) + 360) % 360
                
                telemetry_list.append(
                    DriverTelemetryResponse(
                        id=driver.id,
                        name=driver.name,
                        vehicle_model=driver.vehicle_model,
                        vehicle_plate=driver.vehicle_plate,
                        vehicle_type=driver.vehicle_type,
                        rating=driver.rating,
                        coords=[driver.lat, driver.lng],
                        heading=driver.heading,
                        speed_kmh=driver.speed_kmh,
                        status="busy" if driver.is_busy else "available"
                    )
                )
            db.commit()
            db.close()

            if ws_manager.active_connections:
                payload = TelemetryBroadcast(
                    timestamp=datetime.utcnow().isoformat(),
                    active_units=len(telemetry_list),
                    fleet=telemetry_list
                ).model_dump()
                await ws_manager.broadcast_json(payload)

        except Exception as err:
            print(f"[Telemetry Stream Error]: {err}")

        await asyncio.sleep(2.5)

# -------------------------------------------------------------
# Lifespan Handler
# -------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    task = asyncio.create_task(background_telemetry_stream())
    yield
    task.cancel()

# -------------------------------------------------------------
# FastAPI Application Declaration
# -------------------------------------------------------------
app = FastAPI(
    title="OmniPulse Core Mobility & Dispatch API",
    description="Production-grade high performance backend for inDrive fare bidding, Uber instant dispatch, and real-time fleet telemetry.",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------
# API Endpoints
# -------------------------------------------------------------

@app.get("/", tags=["Health & Metadata"])
def api_root():
    return {
        "platform": "OmniPulse Mobility Backend",
        "status": "online",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0",
        "telemetry_websocket": "/ws/fleet",
        "documentation": "/docs"
    }

@app.post("/fare-estimate", response_model=FareEstimateResponse, tags=["Rides & Pricing"])
def calculate_fare_estimate(payload: FareEstimateRequest):
    """
    Computes dynamic baseline fares for all vehicle types.
    Matches exact formulas:
    - Auto Rickshaw: $4.00 Base + $1.00/km (At 5.4 km -> $9.40)
    - Economy Hatchback: $6.00 Base + $1.35/km (At 5.4 km -> $13.29)
    - Moto Express: $3.00 Base + $0.80/km (At 5.4 km -> $7.32)
    - Comfort Sedan: $8.50 Base + $1.75/km (At 5.4 km -> $17.95)
    """
    # Use provided distance or compute via Haversine
    distance_km = payload.distance_km if payload.distance_km is not None else calculate_haversine_distance(
        payload.pickup_lat, payload.pickup_lng, payload.dropoff_lat, payload.dropoff_lng
    )
    
    # Minimum route distance guard
    effective_distance = max(1.0, distance_km)
    duration_mins = max(4, round(effective_distance * 2.2 + 3))

    estimates: List[VehicleEstimate] = []

    for v_type, card in VEHICLE_RATE_CARDS.items():
        base = card["base_fare"]
        per_km = card["per_km_rate"]
        calculated_fare = round(base + (effective_distance * per_km), 2)

        estimates.append(
            VehicleEstimate(
                vehicle_type=v_type,
                name=card["name"],
                base_fare=base,
                per_km_rate=per_km,
                distance_km=effective_distance,
                calculated_fare=calculated_fare,
                eta_minutes=card["eta_mins"],
                capacity=card["capacity"],
                description=card["description"]
            )
        )

    return FareEstimateResponse(
        pickup_coords=[payload.pickup_lat, payload.pickup_lng],
        dropoff_coords=[payload.dropoff_lat, payload.dropoff_lng],
        distance_km=effective_distance,
        duration_minutes=duration_mins,
        estimates=estimates
    )

@app.post("/dispatch", response_model=DispatchResponse, tags=["Dispatch Engine"])
def dispatch_nearest_driver(payload: DispatchRequest, db: Session = Depends(get_db)):
    """
    Finds and dispatches the nearest active driver from the live fleet using spherical geometry.
    Locks driver, generates 4-digit boarding OTP, and creates persistent Trip record in DB.
    """
    distance_km = calculate_haversine_distance(
        payload.pickup_lat, payload.pickup_lng, payload.dropoff_lat, payload.dropoff_lng
    )
    effective_distance = max(1.5, distance_km)

    # Calculate baseline rate
    card = VEHICLE_RATE_CARDS.get(payload.vehicle_type, VEHICLE_RATE_CARDS[VehicleType.SEDAN])
    standard_fare = round(card["base_fare"] + effective_distance * card["per_km_rate"], 2)
    final_fare = payload.customer_offer if (payload.mode == RideMode.INDRIVE and payload.customer_offer) else standard_fare

    # Query active drivers matching vehicle criteria
    query = db.query(Driver).filter(Driver.is_online == True, Driver.is_busy == False)
    eligible_drivers = query.filter(Driver.vehicle_type == payload.vehicle_type.value).all()
    
    # Fallback to any online driver if exact vehicle type is busy
    if not eligible_drivers:
        eligible_drivers = query.all()

    if not eligible_drivers:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="All fleet units are currently on active trips. Please try again in 60 seconds."
        )

    # Sort drivers by Haversine proximity to pickup
    eligible_drivers.sort(
        key=lambda d: calculate_haversine_distance(payload.pickup_lat, payload.pickup_lng, d.lat, d.lng)
    )
    selected_driver = eligible_drivers[0]
    
    driver_dist_km = calculate_haversine_distance(payload.pickup_lat, payload.pickup_lng, selected_driver.lat, selected_driver.lng)
    driver_eta_mins = max(1, round(driver_dist_km * 2.4 + 1))

    # Generate 4-Digit Security OTP
    otp_code = str(random.randint(1000, 9999))

    # Persist Trip
    new_trip = Trip(
        user_id=payload.user_id,
        driver_id=selected_driver.id,
        pickup_name=payload.pickup_name,
        pickup_lat=payload.pickup_lat,
        pickup_lng=payload.pickup_lng,
        dropoff_name=payload.dropoff_name,
        dropoff_lat=payload.dropoff_lat,
        dropoff_lng=payload.dropoff_lng,
        distance_km=effective_distance,
        vehicle_type=payload.vehicle_type.value,
        mode=payload.mode.value,
        customer_offer=payload.customer_offer,
        final_fare=final_fare,
        otp=otp_code,
        status="accepted"
    )
    selected_driver.is_busy = True

    db.add(new_trip)
    db.commit()
    db.refresh(new_trip)

    return DispatchResponse(
        trip_id=new_trip.id,
        mode=payload.mode,
        status=TripStatus.ACCEPTED,
        driver=DriverResponse(
            id=selected_driver.id,
            name=selected_driver.name,
            avatar=selected_driver.avatar,
            phone=selected_driver.phone,
            rating=selected_driver.rating,
            total_trips=selected_driver.total_trips,
            vehicle_model=selected_driver.vehicle_model,
            vehicle_plate=selected_driver.vehicle_plate,
            vehicle_type=selected_driver.vehicle_type,
            lat=selected_driver.lat,
            lng=selected_driver.lng,
            speed_kmh=selected_driver.speed_kmh
        ),
        distance_km=effective_distance,
        final_fare=final_fare,
        otp=otp_code,
        driver_eta_minutes=driver_eta_mins,
        driver_distance_km=driver_dist_km,
        message=f"{selected_driver.name} is navigating to {payload.pickup_name} in a {selected_driver.vehicle_model}."
    )

@app.post("/mode-switch", response_model=ModeSwitchResponse, tags=["inDrive vs Uber Modes"])
def handle_mode_switch(payload: ModeSwitchRequest, db: Session = Depends(get_db)):
    """
    Handles logic switching between 'inDrive Mode' (fare bidding & driver quotes) and 'Uber Instant' (guaranteed fixed fare).
    """
    distance_km = max(1.5, calculate_haversine_distance(
        payload.pickup_lat, payload.pickup_lng, payload.dropoff_lat, payload.dropoff_lng
    ))
    card = VEHICLE_RATE_CARDS.get(payload.vehicle_type, VEHICLE_RATE_CARDS[VehicleType.MINI])
    standard_fare = round(card["base_fare"] + distance_km * card["per_km_rate"], 2)

    driver_bids: List[DriverBidResponse] = []

    if payload.target_mode == RideMode.INDRIVE:
        customer_offer = payload.customer_offer if payload.customer_offer else round(standard_fare * 0.9, 2)
        drivers = db.query(Driver).filter(Driver.is_online == True).limit(3).all()
        
        for idx, drv in enumerate(drivers):
            drv_dist = calculate_haversine_distance(payload.pickup_lat, payload.pickup_lng, drv.lat, drv.lng)
            eta = max(2, round(drv_dist * 2.2 + 1))
            
            if idx == 0 and customer_offer >= standard_fare * 0.88:
                offered_fare = customer_offer
                is_exact = True
            else:
                offered_fare = round(customer_offer + (1.20 if idx == 1 else 2.00), 2)
                is_exact = False

            driver_bids.append(
                DriverBidResponse(
                    driver_id=drv.id,
                    driver_name=drv.name,
                    avatar=drv.avatar,
                    rating=drv.rating,
                    vehicle_model=drv.vehicle_model,
                    vehicle_plate=drv.vehicle_plate,
                    offered_fare=offered_fare,
                    eta_minutes=eta,
                    driver_distance_km=drv_dist,
                    is_exact_match=is_exact
                )
            )
        strategy = f"inDrive Fair Bidding active: {len(driver_bids)} drivers submitted live counter-quotes."
    else:
        customer_offer = None
        strategy = f"Uber Instant active: Guaranteed dispatch locked at fixed fare of ${standard_fare:.2f}."

    return ModeSwitchResponse(
        active_mode=payload.target_mode,
        vehicle_type=payload.vehicle_type,
        distance_km=distance_km,
        standard_fare=standard_fare,
        customer_offer=customer_offer,
        driver_bids=driver_bids,
        strategy_summary=strategy
    )

@app.get("/drivers", response_model=List[DriverResponse], tags=["Fleet & Drivers"])
def list_fleet_drivers(db: Session = Depends(get_db)):
    """Retrieves all active units in the live fleet with coordinates and ratings."""
    drivers = db.query(Driver).all()
    return [
        DriverResponse(
            id=d.id,
            name=d.name,
            avatar=d.avatar,
            phone=d.phone,
            rating=d.rating,
            total_trips=d.total_trips,
            vehicle_model=d.vehicle_model,
            vehicle_plate=d.vehicle_plate,
            vehicle_type=d.vehicle_type,
            lat=d.lat,
            lng=d.lng,
            speed_kmh=d.speed_kmh
        )
        for d in drivers
    ]

@app.get("/trips/{trip_id}", tags=["Trips"])
def get_trip_details(trip_id: int, db: Session = Depends(get_db)):
    """Retrieves a trip by ID with assigned driver and OTP status."""
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip

# -------------------------------------------------------------
# WebSocket Live Stream for Fleet Map Overlays
# -------------------------------------------------------------
@app.websocket("/ws/fleet")
async def websocket_fleet_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint broadcasting real-time driver coordinates and telemetry
    to Leaflet / Carto / Google Maps instances every 2.5 seconds.
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep-alive heartbeat listener
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)

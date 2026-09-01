from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime

class RideMode(str, Enum):
    INDRIVE = "indrive"
    UBER = "uber"

class VehicleType(str, Enum):
    BIKE = "bike"
    RICKSHAW = "rickshaw"
    MINI = "mini"
    SEDAN = "sedan"
    SUV = "suv"
    DELIVERY = "delivery"

class TripStatus(str, Enum):
    SEARCHING = "searching"
    BIDDING = "bidding"
    ACCEPTED = "accepted"
    ARRIVED = "arrived"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

# -------------------------------------------------------------
# Pricing Configuration Constants (Baseline rates)
# -------------------------------------------------------------
VEHICLE_RATE_CARDS: Dict[VehicleType, Dict[str, Any]] = {
    VehicleType.RICKSHAW: {
        "name": "Auto Rickshaw",
        "base_fare": 4.00,
        "per_km_rate": 1.00,
        "capacity": "3 Passengers � Open Air",
        "description": "Economical 3-wheeler for fast city hops ($9.40 baseline at 5.4 km)",
        "eta_mins": 3
    },
    VehicleType.MINI: {
        "name": "Economy Hatchback",
        "base_fare": 6.00,
        "per_km_rate": 1.35,
        "capacity": "4 Passengers � Air Conditioned",
        "description": "Affordable daily AC compact car ($13.29 baseline at 5.4 km)",
        "eta_mins": 4
    },
    VehicleType.BIKE: {
        "name": "Moto Express",
        "base_fare": 3.00,
        "per_km_rate": 0.80,
        "capacity": "1 Rider � Helmet Provided",
        "description": "Rapid solo motorbike commuter",
        "eta_mins": 2
    },
    VehicleType.SEDAN: {
        "name": "Comfort Sedan",
        "base_fare": 8.50,
        "per_km_rate": 1.75,
        "capacity": "4 Passengers � Extra Legroom",
        "description": "Spacious premium sedan (Corolla, Civic, Camry)",
        "eta_mins": 5
    },
    VehicleType.SUV: {
        "name": "Executive SUV",
        "base_fare": 12.00,
        "per_km_rate": 2.30,
        "capacity": "6 Passengers � Large Luggage Space",
        "description": "High-capacity luxury SUV (Highlander, Tahoe)",
        "eta_mins": 6
    },
    VehicleType.DELIVERY: {
        "name": "Courier Express Box",
        "base_fare": 4.50,
        "per_km_rate": 0.95,
        "capacity": "Up to 25kg Box",
        "description": "Instant courier delivery with live proof of delivery",
        "eta_mins": 3
    }
}

# -------------------------------------------------------------
# Fare Estimation Schemas
# -------------------------------------------------------------
class FareEstimateRequest(BaseModel):
    pickup_lat: float = Field(..., example=40.7128)
    pickup_lng: float = Field(..., example=-74.0060)
    dropoff_lat: float = Field(..., example=40.7589)
    dropoff_lng: float = Field(..., example=-73.9851)
    distance_km: Optional[float] = Field(None, description="Optional override distance in km (e.g. 5.4 km)", example=5.4)

class VehicleEstimate(BaseModel):
    vehicle_type: VehicleType
    name: str
    base_fare: float
    per_km_rate: float
    distance_km: float
    calculated_fare: float
    eta_minutes: int
    capacity: str
    description: str

class FareEstimateResponse(BaseModel):
    pickup_coords: List[float]
    dropoff_coords: List[float]
    distance_km: float
    duration_minutes: int
    estimates: List[VehicleEstimate]

# -------------------------------------------------------------
# Dispatch Schemas
# -------------------------------------------------------------
class DispatchRequest(BaseModel):
    pickup_lat: float = Field(..., example=40.7128)
    pickup_lng: float = Field(..., example=-74.0060)
    dropoff_lat: float = Field(..., example=40.7589)
    dropoff_lng: float = Field(..., example=-73.9851)
    pickup_name: str = Field(default="Current Location", example="742 Evergreen Terrace")
    dropoff_name: str = Field(default="Destination", example="Silicon Boulevard Tower A")
    vehicle_type: VehicleType = Field(default=VehicleType.SEDAN)
    mode: RideMode = Field(default=RideMode.UBER, description="'indrive' for fare bidding or 'uber' for instant dispatch")
    customer_offer: Optional[float] = Field(None, description="Required for inDrive mode", example=14.50)
    user_id: Optional[int] = Field(None, example=1)

class DriverResponse(BaseModel):
    id: int
    name: str
    avatar: Optional[str]
    phone: str
    rating: float
    total_trips: int
    vehicle_model: str
    vehicle_plate: str
    vehicle_type: str
    lat: float
    lng: float
    speed_kmh: float

class DispatchResponse(BaseModel):
    trip_id: int
    mode: RideMode
    status: TripStatus
    driver: DriverResponse
    distance_km: float
    final_fare: float
    otp: str
    driver_eta_minutes: int
    driver_distance_km: float
    message: str

# -------------------------------------------------------------
# Mode Switch Schemas
# -------------------------------------------------------------
class ModeSwitchRequest(BaseModel):
    pickup_lat: float = Field(..., example=40.7128)
    pickup_lng: float = Field(..., example=-74.0060)
    dropoff_lat: float = Field(..., example=40.7589)
    dropoff_lng: float = Field(..., example=-73.9851)
    vehicle_type: VehicleType = Field(default=VehicleType.MINI)
    target_mode: RideMode = Field(..., example=RideMode.INDRIVE)
    customer_offer: Optional[float] = Field(None, description="Proposed fare when switching to inDrive mode", example=12.00)

class DriverBidResponse(BaseModel):
    driver_id: int
    driver_name: str
    avatar: Optional[str]
    rating: float
    vehicle_model: str
    vehicle_plate: str
    offered_fare: float
    eta_minutes: int
    driver_distance_km: float
    is_exact_match: bool

class ModeSwitchResponse(BaseModel):
    active_mode: RideMode
    vehicle_type: VehicleType
    distance_km: float
    standard_fare: float
    customer_offer: Optional[float]
    driver_bids: List[DriverBidResponse]
    strategy_summary: str

# -------------------------------------------------------------
# Real-Time Telemetry Schemas
# -------------------------------------------------------------
class DriverTelemetryResponse(BaseModel):
    id: int
    name: str
    vehicle_model: str
    vehicle_plate: str
    vehicle_type: str
    rating: float
    coords: List[float]
    heading: float
    speed_kmh: float
    status: str

class TelemetryBroadcast(BaseModel):
    event: str = "fleet_telemetry"
    timestamp: str
    active_units: int
    fleet: List[DriverTelemetryResponse]

from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING
from pymongo.errors import DuplicateKeyError

load_dotenv()
client = MongoClient(os.getenv("MONGODB_URI"), tz_aware=True)
db = client["tutorial6"]
devices = db["devices"]
readings = db["readings"]
devices.create_index([("mac", ASCENDING)], unique=True)

app = FastAPI()


class Device(BaseModel):
    mac: str
    name: str | None = None
    room: str | None = None


class Reading(BaseModel):
    mac: str
    temp: float


@app.get("/devices")
def get_devices():
    return list(devices.find({}, {"_id": 0}))


@app.get("/devices/{mac}")
def get_device(mac: str):
    device = devices.find_one({"mac": mac}, {"_id": 0})
    if device is None:
        raise HTTPException(status_code=404, detail="It nuh deh deh. hush.")
    return device


@app.post("/devices", status_code=201)
def create_device(device: Device):
    new_device = device.model_dump()
    try:
        devices.insert_one(new_device)
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail=f"Device with MAC {device.mac} already exists. hush.")
    new_device.pop("_id")
    return new_device


@app.post("/readings", status_code=201)
def create_reading(reading: Reading):
    if devices.find_one({"mac": reading.mac}) is None:
        raise HTTPException(status_code=404, detail="No device with MAC " + reading.mac)
    new_reading = reading.model_dump()
    new_reading["time"] = datetime.now(timezone.utc)
    readings.insert_one(new_reading)
    new_reading.pop("_id")
    return new_reading


@app.get("/readings")
def get_readings(mac: str | None = None, since: datetime | None = None, limit: int = 10):
    query = {}
    if mac is not None:
        query["mac"] = mac
    if since is not None:
        query["time"] = {"$gte": since}
    return list(readings.find(query, {"_id": 0}).sort("time", -1).limit(limit))


@app.get("/readings/latest")
def get_latest_reading(mac: str | None = None):
    query = {}
    if mac is not None:
        query["mac"] = mac
    reading = readings.find_one(query, {"_id": 0}, sort=[("time", -1)])
    if reading is None:
        raise HTTPException(status_code=404, detail="No readings yet")
    return reading
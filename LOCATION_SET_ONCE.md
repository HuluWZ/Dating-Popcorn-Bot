# Location Set Only Once - Implementation

## 🎯 **Location Immutability**

The user location can only be set **once** and cannot be changed afterward. This ensures location data integrity and prevents location spoofing.

## 🔒 **Location Constraint Implementation**

### **User Model Protection:**
```python
def set_location(self, latitude: float, longitude: float):
    """Set user location using PostGIS POINT (only once)"""
    if self.location is not None:
        raise ValueError("Location can only be set once and cannot be changed")
    
    point = Point(longitude, latitude)  # PostGIS uses (longitude, latitude)
    self.location = from_shape(point, srid=4326)
    self.updated_at = datetime.utcnow()
```

### **Database Service Protection:**
```python
async def set_user_location(telegram_id: str, latitude: float, longitude: float) -> bool:
    """Set user location (only once)"""
    # Check if location is already set
    if user.location is not None:
        logger.warning(f"User {telegram_id} already has location set")
        return False
    
    user.set_location(latitude, longitude)
    await session.commit()
    return True
```

## 🚀 **Usage Examples:**

### **Setting Location (First Time):**
```python
# First time setting location - SUCCESS
success = await SimpleDatabase.set_user_location(
    telegram_id="123456789",
    latitude=40.7128,
    longitude=-74.0060
)
print(success)  # True
```

### **Trying to Set Location Again:**
```python
# Second time setting location - FAILS
success = await SimpleDatabase.set_user_location(
    telegram_id="123456789",
    latitude=41.0000,  # Different location
    longitude=-75.0000
)
print(success)  # False - Location already set
```

### **Check if User Has Location:**
```python
# Check if user has location set
has_location = await SimpleDatabase.has_user_location("123456789")
if has_location:
    print("User has location set")
else:
    print("User needs to set location")
```

### **Get User Location:**
```python
# Get user location (if set)
location = await SimpleDatabase.get_user_location("123456789")
if location:
    lat, lng = location
    print(f"User location: {lat}, {lng}")
else:
    print("User has no location set")
```

## 🔧 **Telegram Bot Integration:**

### **Location Request Handler:**
```python
async def handle_location_request(message):
    user_id = str(message.from_user.id)
    
    # Check if user already has location
    has_location = await SimpleDatabase.has_user_location(user_id)
    
    if has_location:
        await message.reply("You have already shared your location. It cannot be changed.")
        return
    
    await message.reply("Please share your location to continue.")
```

### **Location Share Handler:**
```python
async def handle_location_share(message):
    user_id = str(message.from_user.id)
    lat = message.location.latitude
    lng = message.location.longitude
    
    # Try to set location (only works if not already set)
    success = await SimpleDatabase.set_user_location(user_id, lat, lng)
    
    if success:
        await message.reply("Location saved successfully!")
    else:
        await message.reply("You have already shared your location. It cannot be changed.")
```

## 🛡️ **Security Benefits:**

### **✅ Prevents Location Spoofing:**
- Users cannot change their location after setting it
- Prevents gaming the system with fake locations
- Ensures location data integrity

### **✅ Data Integrity:**
- Location is set once and remains consistent
- No location history or changes to track
- Simpler data model

### **✅ User Experience:**
- Clear expectation that location is set once
- No confusion about location changes
- Prevents accidental location updates

## 📊 **Database Schema:**

```sql
CREATE TABLE users (
    id VARCHAR PRIMARY KEY,                    -- telegram_id as string
    username VARCHAR,
    location GEOMETRY(POINT, 4326),           -- PostGIS POINT (set once)
    is_banned BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
);
```

## 🔍 **Location Status Methods:**

### **Check Location Status:**
```python
# Check if user has location
has_location = await SimpleDatabase.has_user_location("123456789")

# Get location if set
location = await SimpleDatabase.get_user_location("123456789")

# Set location (only if not already set)
success = await SimpleDatabase.set_user_location("123456789", lat, lng)
```

## 🚫 **What Happens on Second Attempt:**

### **Model Level Protection:**
```python
# This will raise ValueError
user.set_location(40.7128, -74.0060)  # First time - OK
user.set_location(41.0000, -75.0000)  # Second time - ValueError!
```

### **Service Level Protection:**
```python
# This will return False
success1 = await SimpleDatabase.set_user_location("123", 40.7128, -74.0060)  # True
success2 = await SimpleDatabase.set_user_location("123", 41.0000, -75.0000)  # False
```

## 🎯 **Use Cases:**

### **✅ Perfect For:**
- Dating apps (location set once for matching)
- Location-based services (one-time setup)
- Privacy-focused applications
- Anti-spoofing requirements

### **❌ Not Suitable For:**
- Real-time tracking applications
- Location history requirements
- Frequent location updates
- Travel/movement tracking

## 🚀 **Implementation Benefits:**

- ✅ **Security** - Prevents location spoofing
- ✅ **Simplicity** - One location per user
- ✅ **Integrity** - Immutable location data
- ✅ **Performance** - No location update queries
- ✅ **Privacy** - Location set once, not tracked

The location is now truly "set only once" with proper protection at both the model and service levels! 🔒

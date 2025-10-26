# PostGIS Location Field Usage

## 🎯 **PostGIS POINT Geometry Implementation**

The User model now uses PostGIS POINT geometry for the location field, providing powerful spatial capabilities.

## 📍 **Database Schema with PostGIS:**

### **User Table:**
```sql
CREATE TABLE users (
    id VARCHAR PRIMARY KEY,                    -- telegram_id as string
    username VARCHAR,
    location GEOMETRY(POINT, 4326),           -- PostGIS POINT geometry
    is_banned BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Create spatial index for better performance
CREATE INDEX idx_users_location ON users USING GIST (location);
```

## 🔧 **How to Use PostGIS Location:**

### **Setting Location:**
```python
# Method 1: Using set_location method (recommended)
user.set_location(40.7128, -74.0060)  # (latitude, longitude)

# Method 2: Using location_coords property
user.location_coords = (40.7128, -74.0060)

# Method 3: Direct PostGIS geometry (advanced)
from shapely.geometry import Point
from geoalchemy2.shape import from_shape
point = Point(-74.0060, 40.7128)  # (longitude, latitude)
user.location = from_shape(point, srid=4326)
```

### **Getting Location:**
```python
# Method 1: Using get_location method (recommended)
location = user.get_location()  # Returns (latitude, longitude) tuple or None

# Method 2: Using location_coords property
location = user.location_coords

# Method 3: Direct PostGIS geometry access (advanced)
if user.location:
    from geoalchemy2.shape import to_shape
    point = to_shape(user.location)
    lat, lng = point.y, point.x  # (latitude, longitude)
```

## 🚀 **PostGIS Geographic Queries:**

### **Find Nearby Reviews (Using PostGIS):**
```python
# Find reviews within 50km radius using PostGIS ST_DWithin
reviews = await SimpleDatabase.find_nearby_reviews(
    latitude=40.7128,
    longitude=-74.0060,
    radius_km=50,
    limit=10
)
```

### **Advanced PostGIS Queries:**
```python
# Find users within radius using PostGIS
from geoalchemy2.functions import ST_DWithin, ST_GeomFromText

center_point = ST_GeomFromText('POINT(-74.0060 40.7128)', 4326)
users = await session.execute(
    select(User).where(
        ST_DWithin(User.location, center_point, 50000)  # 50km in meters
    )
)
```

## 📊 **PostGIS Functions Available:**

### **Distance Calculations:**
```python
from geoalchemy2.functions import ST_Distance

# Calculate distance between two points
distance = ST_Distance(user1.location, user2.location)
```

### **Spatial Operations:**
```python
from geoalchemy2.functions import ST_GeomFromText, ST_AsText

# Create point from coordinates
point = ST_GeomFromText('POINT(-74.0060 40.7128)', 4326)

# Convert geometry to text
text_geom = ST_AsText(user.location)
```

### **Bounding Box Queries:**
```python
from geoalchemy2.functions import ST_MakeEnvelope

# Find users within bounding box
bbox = ST_MakeEnvelope(-74.1, 40.7, -73.9, 40.8, 4326)
users = await session.execute(
    select(User).where(
        ST_Within(User.location, bbox)
    )
)
```

## 🗄️ **Database Operations:**

### **Create User with Location:**
```python
# Create user
user = await SimpleDatabase.create_or_get_user(
    telegram_id="123456789",
    username="john_doe"
)

# Set location using PostGIS
user.set_location(40.7128, -74.0060)
await session.commit()
```

### **Update User Location:**
```python
# Update location using PostGIS
await SimpleDatabase.update_user_location(
    telegram_id="123456789",
    latitude=40.7128,
    longitude=-74.0060
)
```

### **Get User Location:**
```python
# Get location as tuple
location = await SimpleDatabase.get_user_location("123456789")
if location:
    lat, lng = location
    print(f"User is at: {lat}, {lng}")
```

## 🔍 **Geographic Queries Examples:**

### **Find Reviews by Distance:**
```python
# Find reviews within 25km
reviews = await SimpleDatabase.find_nearby_reviews(
    latitude=40.7128,
    longitude=-74.0060,
    radius_km=25,
    limit=5
)
```

### **Advanced Spatial Queries:**
```python
# Find users within specific area
from geoalchemy2.functions import ST_Contains, ST_MakePolygon, ST_GeomFromText

# Define a polygon area
polygon = ST_GeomFromText('POLYGON((-74.1 40.7, -73.9 40.7, -73.9 40.8, -74.1 40.8, -74.1 40.7))', 4326)

users = await session.execute(
    select(User).where(
        ST_Contains(polygon, User.location)
    )
)
```

## 📈 **Performance Benefits:**

### **Spatial Indexing:**
```sql
-- Create GIST index for fast spatial queries
CREATE INDEX idx_users_location ON users USING GIST (location);
```

### **Optimized Queries:**
- ✅ **ST_DWithin** - Fast radius queries
- ✅ **ST_Distance** - Accurate distance calculations
- ✅ **Spatial indexes** - GIST indexes for performance
- ✅ **Coordinate systems** - Proper SRID handling

## 🎯 **Coordinate System (SRID 4326):**

- **SRID 4326** - WGS84 (World Geodetic System 1984)
- **Standard for GPS coordinates**
- **Used by most mapping services**
- **Compatible with Google Maps, OpenStreetMap, etc.**

## 🚀 **Benefits of PostGIS:**

### **✅ Spatial Capabilities:**
- Accurate distance calculations
- Spatial indexing for performance
- Complex geometric operations
- Coordinate system support

### **✅ Performance:**
- GIST spatial indexes
- Optimized spatial queries
- Efficient radius searches
- Fast distance calculations

### **✅ Standards Compliance:**
- OGC (Open Geospatial Consortium) compliant
- Standard SQL spatial functions
- Industry-standard coordinate systems

## 🔧 **Setup Requirements:**

### **Dependencies:**
```bash
# PostGIS dependencies
geoalchemy2==0.14.2
shapely==2.0.2
```

### **Database:**
```yaml
# Docker Compose
postgres:
  image: postgis/postgis:17-3.4-alpine
```

### **Extensions:**
```sql
-- Required PostGIS extensions
CREATE EXTENSION postgis;
CREATE EXTENSION postgis_topology;
```

## 🎉 **Result:**

You now have a powerful PostGIS-enabled location system with:
- ✅ **PostGIS POINT geometry** for location storage
- ✅ **Spatial indexing** for performance
- ✅ **Geographic queries** using PostGIS functions
- ✅ **Distance calculations** with ST_Distance
- ✅ **Radius searches** with ST_DWithin
- ✅ **Coordinate system support** (SRID 4326)

The location field is now a proper PostGIS POINT geometry with full spatial capabilities! 🎯

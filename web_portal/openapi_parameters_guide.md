# OpenAPI Parameters Guide for Backend Developers

## Table of Contents
1. [What is openapi.Parameter?](#what-is-openapiparameter)
2. [Usage in Django REST Framework](#usage-in-django-rest-framework)
3. [Parameter Types](#parameter-types)
4. [Important Backend Terms for Interviews](#important-backend-terms-for-interviews)

---

## What is openapi.Parameter?

`openapi.Parameter` is a class used in **Django REST Framework (DRF)** with **drf-spectacular** or similar libraries to define API parameters in OpenAPI/Swagger documentation.

### Purpose
- **API Documentation**: Automatically generates interactive API documentation (Swagger UI)
- **Parameter Definition**: Explicitly defines query parameters, path parameters, headers, etc.
- **Type Safety**: Ensures proper data types and validation rules are documented
- **Developer Experience**: Helps frontend developers understand API requirements

### Basic Syntax
```python
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

@extend_schema(
    parameters=[
        OpenApiParameter(
            name='database',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Database name to query',
            required=True
        )
    ]
)
def my_api_view(request):
    database = request.query_params.get('database')
    # Your logic here
```

---

## Usage in Django REST Framework

### 1. Query Parameters
Used in URL query strings: `/api/users?status=active&page=1`

```python
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.decorators import api_view
from rest_framework.response import Response

@extend_schema(
    parameters=[
        OpenApiParameter(
            name='status',
            type=str,
            location=OpenApiParameter.QUERY,
            description='Filter by user status',
            required=False,
            enum=['active', 'inactive', 'pending']
        ),
        OpenApiParameter(
            name='page',
            type=int,
            location=OpenApiParameter.QUERY,
            description='Page number for pagination',
            required=False,
            default=1
        )
    ]
)
@api_view(['GET'])
def list_users(request):
    status = request.query_params.get('status')
    page = request.query_params.get('page', 1)
    # Your logic
    return Response({'status': status, 'page': page})
```

### 2. Path Parameters
Used in URL paths: `/api/users/123/`

```python
@extend_schema(
    parameters=[
        OpenApiParameter(
            name='id',
            type=int,
            location=OpenApiParameter.PATH,
            description='User ID',
            required=True
        )
    ]
)
@api_view(['GET'])
def get_user(request, id):
    # Your logic
    return Response({'user_id': id})
```

### 3. Header Parameters
Used in HTTP headers

```python
@extend_schema(
    parameters=[
        OpenApiParameter(
            name='X-API-Key',
            type=str,
            location=OpenApiParameter.HEADER,
            description='API authentication key',
            required=True
        )
    ]
)
@api_view(['GET'])
def protected_endpoint(request):
    api_key = request.headers.get('X-API-Key')
    # Your logic
    return Response({'authenticated': True})
```

### 4. Multiple Parameters Example
```python
@extend_schema(
    parameters=[
        OpenApiParameter(
            name='database',
            type=str,
            location=OpenApiParameter.QUERY,
            description='Database identifier',
            required=True
        ),
        OpenApiParameter(
            name='limit',
            type=int,
            location=OpenApiParameter.QUERY,
            description='Maximum number of results',
            required=False,
            default=10
        ),
        OpenApiParameter(
            name='offset',
            type=int,
            location=OpenApiParameter.QUERY,
            description='Number of results to skip',
            required=False,
            default=0
        )
    ]
)
@api_view(['GET'])
def search_records(request):
    database = request.query_params.get('database')
    limit = int(request.query_params.get('limit', 10))
    offset = int(request.query_params.get('offset', 0))
    # Your logic
    return Response({'results': []})
```

---

## Parameter Types

### Common OpenAPI Types
```python
from drf_spectacular.types import OpenApiTypes

OpenApiTypes.STR      # String
OpenApiTypes.INT      # Integer
OpenApiTypes.FLOAT    # Float/Decimal
OpenApiTypes.BOOL     # Boolean
OpenApiTypes.DATE     # Date (YYYY-MM-DD)
OpenApiTypes.DATETIME # DateTime (ISO 8601)
OpenApiTypes.UUID     # UUID
OpenApiTypes.BINARY   # Binary/File
OpenApiTypes.OBJECT   # JSON Object
```

### Parameter Locations
```python
OpenApiParameter.QUERY   # Query string (?key=value)
OpenApiParameter.PATH    # URL path (/users/{id}/)
OpenApiParameter.HEADER  # HTTP headers
OpenApiParameter.COOKIE  # Cookies
```

---

## Important Backend Terms for Interviews

### 1. **REST (Representational State Transfer)**
- **Definition**: Architectural style for designing networked applications
- **Key Principles**:
  - Stateless communication
  - Client-server architecture
  - Cacheable responses
  - Uniform interface
- **Interview Question**: "Explain the difference between PUT and PATCH?"
  - **PUT**: Replace entire resource
  - **PATCH**: Partial update of resource

### 2. **HTTP Methods (Verbs)**
| Method | Purpose | Idempotent | Safe |
|--------|---------|------------|------|
| GET | Retrieve data | ✅ | ✅ |
| POST | Create resource | ❌ | ❌ |
| PUT | Update/Replace | ✅ | ❌ |
| PATCH | Partial update | ❌ | ❌ |
| DELETE | Remove resource | ✅ | ❌ |

- **Idempotent**: Multiple identical requests have same effect as single request
- **Safe**: Does not modify server state

### 3. **HTTP Status Codes**
```
2xx - Success
  200 OK - Request succeeded
  201 Created - Resource created successfully
  204 No Content - Success but no content to return

3xx - Redirection
  301 Moved Permanently
  302 Found (Temporary redirect)

4xx - Client Errors
  400 Bad Request - Invalid syntax
  401 Unauthorized - Authentication required
  403 Forbidden - No permission
  404 Not Found - Resource doesn't exist
  422 Unprocessable Entity - Validation error

5xx - Server Errors
  500 Internal Server Error
  502 Bad Gateway
  503 Service Unavailable
```

### 4. **API Authentication Methods**

#### Token-Based Authentication
```python
# Example: JWT (JSON Web Token)
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### API Key Authentication
```python
# Header-based
X-API-Key: your-api-key-here

# Query parameter
/api/data?api_key=your-api-key-here
```

#### OAuth 2.0
- Industry standard for authorization
- Used by Google, Facebook, GitHub APIs

### 5. **Database Concepts**

#### ACID Properties
- **Atomicity**: All or nothing transactions
- **Consistency**: Data remains valid after transactions
- **Isolation**: Concurrent transactions don't interfere
- **Durability**: Committed data persists

#### Normalization
- **1NF**: Eliminate repeating groups
- **2NF**: Remove partial dependencies
- **3NF**: Remove transitive dependencies

#### Indexes
```sql
-- Speed up queries but slow down writes
CREATE INDEX idx_user_email ON users(email);
```

### 6. **ORM (Object-Relational Mapping)**
```python
# Django ORM Example
from django.db import models

class User(models.Model):
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

# Query
users = User.objects.filter(email__contains='@gmail.com')
```

**Interview Question**: "What is N+1 query problem?"

#### The Problem
The N+1 query problem occurs when your code executes 1 query to fetch N records, then N additional queries to fetch related data for each record.

**Example Scenario:**
```python
# BAD - N+1 Query Problem
# Fetching 100 sales staff profiles
staff_members = SalesStaffProfile.objects.all()  # 1 query

for staff in staff_members:  # Loop through 100 records
    print(staff.user.email)  # 100 additional queries!
    # Total: 1 + 100 = 101 queries
```

**What happens:**
1. **Query 1**: `SELECT * FROM sales_staff_profile` (fetches 100 records)
2. **Query 2**: `SELECT * FROM user WHERE id = 1` (for first staff)
3. **Query 3**: `SELECT * FROM user WHERE id = 2` (for second staff)
4. ... (98 more queries)
5. **Query 101**: `SELECT * FROM user WHERE id = 100` (for last staff)

**Performance Impact:**
- 100 staff members = 101 database queries
- 1000 staff members = 1001 database queries
- **Massive performance degradation!**

#### Solution 1: `select_related()` (For ForeignKey & OneToOne)

Use `select_related()` for **forward ForeignKey** and **OneToOne** relationships. It performs a SQL JOIN.

```python
# GOOD - Using select_related()
staff_members = SalesStaffProfile.objects.select_related('user').all()

for staff in staff_members:
    print(staff.user.email)  # No additional queries!
    # Total: 1 query only
```

**Generated SQL:**
```sql
SELECT 
    sales_staff_profile.*,
    user.*
FROM sales_staff_profile
INNER JOIN user ON sales_staff_profile.user_id = user.id
```

**When to use `select_related()`:**
- ForeignKey relationships (e.g., `staff.user`, `order.customer`)
- OneToOne relationships (e.g., `user.profile`)
- Following relationships "forward" (from the model with the ForeignKey)

**Multiple relationships:**
```python
# Select multiple related objects
staff = SalesStaffProfile.objects.select_related(
    'user',
    'designation',
    'manager'
).all()

for s in staff:
    print(s.user.email)          # No extra query
    print(s.designation.name)     # No extra query
    print(s.manager.user.email)   # No extra query
```

#### Solution 2: `prefetch_related()` (For ManyToMany & Reverse ForeignKey)

Use `prefetch_related()` for **ManyToMany** and **reverse ForeignKey** relationships. It performs separate queries and joins in Python.

```python
# GOOD - Using prefetch_related()
staff_members = SalesStaffProfile.objects.prefetch_related('territories').all()

for staff in staff_members:
    for territory in staff.territories.all():  # No additional queries!
        print(territory.name)
    # Total: 2 queries (1 for staff, 1 for all territories)
```

**Generated SQL:**
```sql
-- Query 1: Get all staff
SELECT * FROM sales_staff_profile

-- Query 2: Get all related territories in one go
SELECT * FROM territory
INNER JOIN sales_staff_territories ON territory.id = sales_staff_territories.territory_id
WHERE sales_staff_territories.staff_id IN (1, 2, 3, ..., 100)
```

**When to use `prefetch_related()`:**
- ManyToMany relationships (e.g., `staff.territories`, `user.groups`)
- Reverse ForeignKey (e.g., `user.sales_profile`, `manager.subordinates`)
- GenericRelation

**Example from your project:**
```python
# Get staff with all their territories, zones, and regions
staff = SalesStaffProfile.objects.prefetch_related(
    'territories',
    'zones',
    'regions',
    'companies'
).all()

for s in staff:
    print(f"Territories: {s.territories.count()}")  # No extra query
    print(f"Zones: {s.zones.count()}")              # No extra query
```

#### Combining Both

```python
# Complex example: select_related + prefetch_related
staff = SalesStaffProfile.objects.select_related(
    'user',           # ForeignKey
    'designation',    # ForeignKey
    'manager'         # ForeignKey (self-referencing)
).prefetch_related(
    'territories',    # ManyToMany
    'subordinates',   # Reverse ForeignKey
    'subordinates__user'  # Nested prefetch
).all()

# All of this with minimal queries:
for s in staff:
    print(s.user.email)                    # No extra query
    print(s.designation.name)              # No extra query
    print(s.manager.user.email if s.manager else 'No manager')  # No extra query
    
    for territory in s.territories.all():  # No extra query
        print(territory.name)
    
    for sub in s.subordinates.all():       # No extra query
        print(sub.user.email)              # No extra query (nested prefetch)
```

#### Performance Comparison

| Approach | Queries | Time (example) |
|----------|---------|----------------|
| No optimization | 1 + N | 5000ms (for 100 records) |
| `select_related()` | 1 | 50ms |
| `prefetch_related()` | 2 | 100ms |
| Combined | 3-5 | 150ms |

#### Quick Reference

```python
# ForeignKey (forward) - use select_related
staff.user              → select_related('user')
order.customer          → select_related('customer')
profile.designation     → select_related('designation')

# OneToOne - use select_related
user.profile            → select_related('profile')

# ManyToMany - use prefetch_related
staff.territories       → prefetch_related('territories')
user.groups             → prefetch_related('groups')

# Reverse ForeignKey - use prefetch_related
manager.subordinates    → prefetch_related('subordinates')
customer.orders         → prefetch_related('orders')

# Nested relationships - chain with __
staff.manager.user      → select_related('manager__user')
staff.subordinates.user → prefetch_related('subordinates__user')
```

**Pro Tip**: Use Django Debug Toolbar to visualize queries and identify N+1 problems!

### 7. **Serialization**

#### What is Serialization?
**Serialization** is the process of converting complex data types (like Django model instances, QuerySets) into native Python datatypes (dict, list) that can then be easily rendered into JSON, XML, or other content types.

**Deserialization** is the reverse process - converting parsed data (JSON) back into complex types.

#### Why Serialization Matters
- **API Responses**: Convert database models to JSON for API responses
- **Data Validation**: Validate incoming data before saving to database
- **Data Transformation**: Control what fields are exposed in API
- **Nested Relationships**: Handle complex object relationships

#### Basic ModelSerializer

```python
from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'first_name', 'last_name']
        read_only_fields = ['id']  # Cannot be modified via API

# Usage
user = User.objects.get(id=1)
serializer = UserSerializer(user)
print(serializer.data)
# Output: {'id': 1, 'email': 'john@example.com', 'username': 'john', ...}
```

#### Serialization vs Deserialization

```python
# SERIALIZATION (Model → JSON)
user = User.objects.get(id=1)
serializer = UserSerializer(user)
json_data = serializer.data  # Python dict
# Can be returned as JSON response

# DESERIALIZATION (JSON → Model)
data = {'email': 'new@example.com', 'username': 'newuser', ...}
serializer = UserSerializer(data=data)
if serializer.is_valid():
    user = serializer.save()  # Creates new User instance
else:
    print(serializer.errors)
```

#### Field Types

```python
class PolicySerializer(serializers.ModelSerializer):
    # Automatically inferred from model
    code = serializers.CharField(max_length=100)
    active = serializers.BooleanField()
    valid_from = serializers.DateField()
    
    # Custom fields
    days_remaining = serializers.SerializerMethodField()
    
    # Read-only computed field
    def get_days_remaining(self, obj):
        if obj.valid_to:
            return (obj.valid_to - timezone.now().date()).days
        return None
    
    class Meta:
        model = Policy
        fields = ['code', 'name', 'active', 'valid_from', 'valid_to', 'days_remaining']
```

#### Nested Serializers

```python
# Example from your project
class DesignationSerializer(serializers.ModelSerializer):
    class Meta:
        model = DesignationModel
        fields = ['code', 'name', 'level']

class SalesStaffProfileSerializer(serializers.ModelSerializer):
    # Nested serializer - shows full designation object
    designation = DesignationSerializer(read_only=True)
    
    # Show email instead of user ID
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    # ManyToMany - list of territory names
    territory_names = serializers.StringRelatedField(
        source='territories',
        many=True,
        read_only=True
    )
    
    class Meta:
        model = SalesStaffProfile
        fields = ['id', 'employee_code', 'designation', 'user_email', 'territory_names']

# Output:
# {
#     "id": 1,
#     "employee_code": "EMP001",
#     "designation": {"code": "FSM", "name": "Farmer Service Manager", "level": 5},
#     "user_email": "john@example.com",
#     "territory_names": ["Lahore", "Karachi"]
# }
```

#### Custom Validation

```python
class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['email', 'username', 'password', 'confirm_password']
    
    # Field-level validation
    def validate_email(self, value):
        """Validate email is unique and from allowed domain"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists")
        
        if not value.endswith('@company.com'):
            raise serializers.ValidationError("Must use company email")
        
        return value
    
    # Object-level validation
    def validate(self, data):
        """Validate passwords match"""
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords don't match")
        
        return data
    
    # Custom create method
    def create(self, validated_data):
        """Hash password before saving"""
        validated_data.pop('confirm_password')  # Remove confirm_password
        password = validated_data.pop('password')
        
        user = User(**validated_data)
        user.set_password(password)  # Hash the password
        user.save()
        return user
```

#### Different Serializers for Different Actions

```python
# List view - minimal data
class UserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'username']

# Detail view - full data
class UserDetailSerializer(serializers.ModelSerializer):
    sales_profile = SalesStaffProfileSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'first_name', 'last_name', 
                  'profile_image', 'date_joined', 'sales_profile']

# Create/Update - writable fields only
class UserWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'username', 'first_name', 'last_name', 'password']
        extra_kwargs = {'password': {'write_only': True}}
```

#### Serializer Methods

```python
class PolicySerializer(serializers.ModelSerializer):
    # Method field - computed value
    status = serializers.SerializerMethodField()
    
    # Custom source - rename field
    policy_code = serializers.CharField(source='code')
    
    # HyperlinkedRelatedField - API URL instead of ID
    url = serializers.HyperlinkedIdentityField(
        view_name='policy-detail',
        lookup_field='code'
    )
    
    def get_status(self, obj):
        """Calculate policy status"""
        if not obj.active:
            return 'inactive'
        if obj.valid_to and obj.valid_to < timezone.now().date():
            return 'expired'
        return 'active'
    
    class Meta:
        model = Policy
        fields = ['url', 'policy_code', 'name', 'status', 'valid_from', 'valid_to']
```

#### Real-World Example from Your Project

```python
# Disease identification with recommended products
class RecommendedProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecommendedProduct
        fields = ['product_item_code', 'product_name', 'dosage', 
                  'application_method', 'priority', 'effectiveness_rating']

class DiseaseIdentificationSerializer(serializers.ModelSerializer):
    # Nested list of recommended products
    recommended_products = RecommendedProductSerializer(many=True, read_only=True)
    
    # Count of products
    product_count = serializers.SerializerMethodField()
    
    def get_product_count(self, obj):
        return obj.recommended_products.filter(is_active=True).count()
    
    class Meta:
        model = DiseaseIdentification
        fields = ['item_code', 'disease_name', 'description', 
                  'product_count', 'recommended_products']

# Output:
# {
#     "item_code": "DIS001",
#     "disease_name": "Leaf Blight",
#     "description": "Common fungal disease...",
#     "product_count": 3,
#     "recommended_products": [
#         {
#             "product_item_code": "FG00581",
#             "product_name": "Jadogar 25 Od",
#             "dosage": "500ml per acre",
#             "priority": 1,
#             "effectiveness_rating": 8.5
#         },
#         ...
#     ]
# }
```

#### Performance Tips

```python
# BAD - N+1 query problem in serializer
class BadStaffSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email')  # Causes N+1!
    
    class Meta:
        model = SalesStaffProfile
        fields = ['id', 'user_email']

# GOOD - Use select_related in view
class StaffViewSet(viewsets.ModelViewSet):
    queryset = SalesStaffProfile.objects.select_related('user')  # Optimize!
    serializer_class = BadStaffSerializer  # Now it's fine
```

**Interview Question**: "What's the difference between `source` and `SerializerMethodField`?"
- **`source`**: Direct field mapping, simple attribute access
- **`SerializerMethodField`**: Custom logic, computed values, requires `get_<field_name>` method

### 8. **Pagination**
```python
# Limit/Offset Pagination
/api/users?limit=10&offset=20

# Cursor-based Pagination (better for large datasets)
/api/users?cursor=eyJpZCI6MTAwfQ==
```

### 9. **Caching**

#### What is Caching?
**Caching** is storing frequently accessed data in a fast-access storage layer (like RAM) to avoid expensive operations like database queries or API calls.

#### Why Caching Matters
- **Performance**: 100x faster than database queries
- **Scalability**: Reduces database load
- **Cost**: Fewer database connections needed
- **User Experience**: Faster page loads

#### Types of Caching

##### 1. **Application-Level Caching (Redis/Memcached)**

**Redis Example:**
```python
import redis
from django.conf import settings

# Connect to Redis
cache = redis.Redis(
    host='localhost',
    port=6379,
    db=0,
    decode_responses=True  # Auto-decode bytes to strings
)

# SET - Store data with expiration
cache.set('user:1', 'John Doe', ex=3600)  # Expires in 1 hour

# GET - Retrieve data
user = cache.get('user:1')  # Returns 'John Doe'

# SET with JSON
import json
user_data = {'id': 1, 'name': 'John', 'email': 'john@example.com'}
cache.set('user:1:profile', json.dumps(user_data), ex=3600)

# GET JSON
profile = json.loads(cache.get('user:1:profile'))

# DELETE
cache.delete('user:1')

# CHECK existence
if cache.exists('user:1'):
    print("User cached")

# INCR - Atomic increment (useful for counters)
cache.incr('page:views')  # Increment by 1
cache.incrby('page:views', 10)  # Increment by 10

# EXPIRE - Set expiration on existing key
cache.expire('user:1', 7200)  # 2 hours

# TTL - Check time to live
ttl = cache.ttl('user:1')  # Returns seconds remaining
```

##### 2. **Django Cache Framework**

**Configuration (settings.py):**
```python
# Redis backend (recommended for production)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'agrigenie',  # Prefix all keys
        'TIMEOUT': 300,  # Default timeout (5 minutes)
    }
}

# Local memory cache (development only)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
        'OPTIONS': {
            'MAX_ENTRIES': 1000,
            'CULL_FREQUENCY': 3,  # Remove 1/3 when full
        }
    }
}
```

**Using Django Cache:**
```python
from django.core.cache import cache

# SET
cache.set('my_key', 'my_value', timeout=300)  # 5 minutes

# GET
value = cache.get('my_key')
# Returns None if not found

# GET with default
value = cache.get('my_key', default='default_value')

# GET or SET (atomic)
def get_user_data(user_id):
    return User.objects.get(id=user_id)

user = cache.get_or_set(
    f'user:{user_id}',
    lambda: get_user_data(user_id),
    timeout=3600
)

# SET MANY
cache.set_many({
    'user:1': 'John',
    'user:2': 'Jane',
    'user:3': 'Bob'
}, timeout=3600)

# GET MANY
users = cache.get_many(['user:1', 'user:2', 'user:3'])
# Returns: {'user:1': 'John', 'user:2': 'Jane', 'user:3': 'Bob'}

# DELETE
cache.delete('my_key')

# DELETE MANY
cache.delete_many(['user:1', 'user:2'])

# CLEAR ALL
cache.clear()  # Use with caution!

# INCREMENT/DECREMENT
cache.set('counter', 0)
cache.incr('counter')  # Now 1
cache.incr('counter', delta=5)  # Now 6
cache.decr('counter')  # Now 5
```

##### 3. **View-Level Caching**

```python
from django.views.decorators.cache import cache_page

# Cache view for 15 minutes
@cache_page(60 * 15)
def product_list(request):
    products = Product.objects.all()
    return render(request, 'products.html', {'products': products})

# Cache with custom key
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator

@method_decorator(cache_page(60 * 15, key_prefix='api'), name='dispatch')
class ProductListView(APIView):
    def get(self, request):
        products = Product.objects.all()
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)
```

##### 4. **Template Fragment Caching**

```django
{% load cache %}

{% cache 500 sidebar request.user.username %}
    <!-- Expensive sidebar rendering -->
    <div class="sidebar">
        {% for item in menu_items %}
            <a href="{{ item.url }}">{{ item.name }}</a>
        {% endfor %}
    </div>
{% endcache %}
```

##### 5. **Low-Level Cache API (Real-World Example)**

```python
from django.core.cache import cache
from .models import Policy
import logging

logger = logging.getLogger(__name__)

def get_active_policies(database='4B-BIO'):
    """Get active policies with caching"""
    cache_key = f'policies:active:{database}'
    
    # Try cache first
    policies = cache.get(cache_key)
    
    if policies is not None:
        logger.info(f"Cache HIT for {cache_key}")
        return policies
    
    # Cache miss - query database
    logger.info(f"Cache MISS for {cache_key}")
    policies = list(Policy.objects.filter(active=True).values())
    
    # Store in cache for 1 hour
    cache.set(cache_key, policies, timeout=3600)
    
    return policies

def invalidate_policy_cache(database='4B-BIO'):
    """Invalidate cache when policies change"""
    cache_key = f'policies:active:{database}'
    cache.delete(cache_key)
    logger.info(f"Cache invalidated for {cache_key}")

# Usage in views
def sync_policies_from_sap(request):
    database = request.GET.get('database')
    
    # Sync from SAP
    client = SAPClient(database)
    policies = client.get_policies()
    
    # Update database
    for policy_data in policies:
        Policy.objects.update_or_create(
            code=policy_data['code'],
            defaults=policy_data
        )
    
    # Invalidate cache
    invalidate_policy_cache(database)
    
    return Response({'status': 'success'})
```

#### Caching Strategies

##### 1. **Cache-Aside (Lazy Loading)**
Most common pattern - check cache first, load from DB if miss.

```python
def get_user(user_id):
    # Check cache
    user = cache.get(f'user:{user_id}')
    
    if user is None:
        # Load from database
        user = User.objects.get(id=user_id)
        # Store in cache
        cache.set(f'user:{user_id}', user, timeout=3600)
    
    return user
```

##### 2. **Write-Through**
Update cache whenever database is updated.

```python
def update_user(user_id, data):
    # Update database
    user = User.objects.get(id=user_id)
    for key, value in data.items():
        setattr(user, key, value)
    user.save()
    
    # Update cache immediately
    cache.set(f'user:{user_id}', user, timeout=3600)
    
    return user
```

##### 3. **Write-Behind (Write-Back)**
Update cache immediately, update database asynchronously.

```python
from celery import shared_task

def update_user_fast(user_id, data):
    # Update cache immediately
    cache.set(f'user:{user_id}:pending', data, timeout=300)
    
    # Schedule async database update
    update_user_in_db.delay(user_id, data)
    
    return {'status': 'pending'}

@shared_task
def update_user_in_db(user_id, data):
    """Background task to update database"""
    user = User.objects.get(id=user_id)
    for key, value in data.items():
        setattr(user, key, value)
    user.save()
    
    # Update cache with final data
    cache.set(f'user:{user_id}', user, timeout=3600)
```

##### 4. **Time-Based Expiration**
Cache expires after a set time.

```python
# Short-lived cache for frequently changing data
cache.set('stock_price:AAPL', 150.25, timeout=60)  # 1 minute

# Long-lived cache for rarely changing data
cache.set('company_logo', logo_url, timeout=86400)  # 24 hours
```

#### Real-World Example from Your Project

```python
# Caching SAP HANA query results
from django.core.cache import cache
from .hana_connect import territory_summary

def get_territory_summary_cached(emp_id, territory, start_date, end_date, database):
    """Get territory summary with caching"""
    
    # Generate unique cache key
    cache_key = f'hana:territory_summary:{database}:{emp_id}:{territory}:{start_date}:{end_date}'
    
    # Try cache first
    result = cache.get(cache_key)
    
    if result is not None:
        return {'data': result, 'cached': True}
    
    # Cache miss - query HANA
    conn = get_hana_connection(database)
    result = territory_summary(conn, emp_id, territory, None, None, start_date, end_date)
    
    # Cache for 15 minutes (HANA data changes frequently)
    cache.set(cache_key, result, timeout=900)
    
    return {'data': result, 'cached': False}
```

#### Performance Comparison

| Operation | Database | Redis Cache | Improvement |
|-----------|----------|-------------|-------------|
| Simple query | 50ms | 0.5ms | **100x faster** |
| Complex join | 500ms | 0.5ms | **1000x faster** |
| API call | 2000ms | 0.5ms | **4000x faster** |

#### Cache Invalidation Strategies

```python
# 1. Time-based (TTL)
cache.set('data', value, timeout=3600)  # Auto-expires

# 2. Event-based (on data change)
from django.db.models.signals import post_save

@receiver(post_save, sender=Policy)
def invalidate_policy_cache(sender, instance, **kwargs):
    cache.delete(f'policy:{instance.code}')

# 3. Manual invalidation
def clear_user_cache(user_id):
    cache.delete_many([
        f'user:{user_id}',
        f'user:{user_id}:profile',
        f'user:{user_id}:permissions'
    ])

# 4. Pattern-based (delete all matching keys)
# Note: Requires redis-py, not available in Django cache
import redis
r = redis.Redis()
for key in r.scan_iter("user:*"):
    r.delete(key)
```

#### Best Practices

1. **Use meaningful cache keys**
   ```python
   # GOOD
   cache_key = f'hana:policies:{database}:{user_id}:{date}'
   
   # BAD
   cache_key = 'data123'
   ```

2. **Set appropriate timeouts**
   ```python
   # Frequently changing data - short timeout
   cache.set('stock_price', price, timeout=60)
   
   # Rarely changing data - long timeout
   cache.set('country_list', countries, timeout=86400)
   ```

3. **Handle cache failures gracefully**
   ```python
   try:
       data = cache.get('key')
   except Exception as e:
       logger.error(f"Cache error: {e}")
       data = None  # Fall back to database
   ```

4. **Monitor cache hit rate**
   ```python
   # Track hits and misses
   if cache.get('key'):
       cache.incr('cache:hits')
   else:
       cache.incr('cache:misses')
   ```

**Interview Question**: "What are the two hard problems in computer science?"
- Cache invalidation
- Naming things
- Off-by-one errors 😄

### 10. **Middleware**
Software layer between request and response

```python
# Django Middleware Example
class CustomMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Code before view
        response = self.get_response(request)
        # Code after view
        return response
```

### 11. **CORS (Cross-Origin Resource Sharing)**
```python
# Django CORS Headers
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "https://example.com",
]
```

**Interview Question**: "Why do we need CORS?"
- Security mechanism to prevent unauthorized cross-origin requests
- Browsers enforce same-origin policy

### 12. **Rate Limiting**
```python
# Prevent API abuse
from rest_framework.throttling import UserRateThrottle

class CustomRateThrottle(UserRateThrottle):
    rate = '100/hour'
```

### 13. **Webhooks**
- Server-to-server HTTP callbacks
- Event-driven notifications
- Example: Payment gateway notifying your server

### 14. **Message Queues**
```python
# Celery example for async tasks
from celery import shared_task

@shared_task
def send_email(user_id):
    # Long-running task
    pass
```

**Popular Tools**: RabbitMQ, Redis, Apache Kafka

### 15. **Microservices vs Monolith**

| Aspect | Monolith | Microservices |
|--------|----------|---------------|
| Architecture | Single codebase | Multiple services |
| Deployment | All at once | Independent |
| Scaling | Vertical | Horizontal |
| Complexity | Lower | Higher |

### 16. **API Versioning**
```python
# URL versioning
/api/v1/users/
/api/v2/users/

# Header versioning
Accept: application/vnd.myapi.v1+json

# Query parameter
/api/users?version=1
```

### 17. **Database Transactions**
```python
from django.db import transaction

@transaction.atomic
def transfer_money(from_account, to_account, amount):
    from_account.balance -= amount
    from_account.save()
    to_account.balance += amount
    to_account.save()
```

### 18. **SQL Joins**
```sql
-- INNER JOIN: Only matching records
SELECT * FROM orders 
INNER JOIN customers ON orders.customer_id = customers.id;

-- LEFT JOIN: All from left + matching from right
SELECT * FROM customers 
LEFT JOIN orders ON customers.id = orders.customer_id;
```

### 19. **Environment Variables**
```python
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
SECRET_KEY = os.getenv('SECRET_KEY')
```

**Why?**: Keep sensitive data out of source code

### 20. **Testing**

#### Unit Tests
```python
from django.test import TestCase

class UserTestCase(TestCase):
    def test_user_creation(self):
        user = User.objects.create(email='test@example.com')
        self.assertEqual(user.email, 'test@example.com')
```

#### Integration Tests
Test multiple components working together

#### Load Testing
Test system under high traffic (tools: JMeter, Locust)

---

## Common Interview Questions

### 1. **What is the difference between authentication and authorization?**
- **Authentication**: Verifying who you are (login)
- **Authorization**: Verifying what you can access (permissions)

### 2. **Explain RESTful API design principles**
- Use nouns for resources (`/users`, not `/getUsers`)
- Use HTTP methods correctly
- Stateless communication
- Proper status codes
- Versioning

### 3. **How do you handle errors in APIs?**
```python
{
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid email format",
        "details": {
            "field": "email",
            "value": "invalid-email"
        }
    }
}
```

### 4. **What is database indexing and when to use it?**
- Speeds up SELECT queries
- Slows down INSERT/UPDATE/DELETE
- Use on frequently queried columns
- Use on foreign keys

### 5. **Explain the CAP theorem**
- **Consistency**: All nodes see same data
- **Availability**: System always responds
- **Partition Tolerance**: Works despite network failures
- **Trade-off**: Can only guarantee 2 out of 3

### 6. **What is SQL injection and how to prevent it?**
```python
# BAD - Vulnerable to SQL injection
query = f"SELECT * FROM users WHERE email = '{user_input}'"

# GOOD - Use parameterized queries
User.objects.filter(email=user_input)  # Django ORM
# or
cursor.execute("SELECT * FROM users WHERE email = %s", [user_input])
```

### 7. **Difference between synchronous and asynchronous processing?**
- **Synchronous**: Wait for operation to complete
- **Asynchronous**: Continue execution, handle result later
- Use async for: Email sending, file processing, external API calls

### 8. **What is a database migration?**
```python
# Django migration
python manage.py makemigrations
python manage.py migrate
```
- Version control for database schema
- Allows rollback
- Team collaboration

---

## Best Practices

### 1. **API Design**
- Use consistent naming conventions
- Version your APIs
- Provide clear error messages
- Document with OpenAPI/Swagger

### 2. **Security**
- Never store passwords in plain text (use hashing)
- Use HTTPS
- Implement rate limiting
- Validate all inputs
- Use environment variables for secrets

### 3. **Performance**
- Use database indexing wisely
- Implement caching
- Optimize database queries (avoid N+1)
- Use pagination for large datasets
- Compress responses (gzip)

### 4. **Code Quality**
- Write tests
- Use meaningful variable names
- Follow DRY (Don't Repeat Yourself)
- Handle exceptions properly
- Log important events

---

## Conclusion

Understanding `openapi.Parameter` and these backend concepts will help you:
- Build better APIs
- Write cleaner, more maintainable code
- Ace technical interviews
- Communicate effectively with team members

**Pro Tip**: Practice implementing these concepts in real projects. Theory is important, but hands-on experience is invaluable!

---

# Technologies & Patterns Used in This Project

This section covers the **actual technologies, patterns, and concepts** used in your Django Web Portal project.

## 1. **SAP Business One Integration**

### What is SAP B1?
SAP Business One is an ERP (Enterprise Resource Planning) system for small and medium-sized businesses.

### SAP Service Layer (B1S)
Your project integrates with SAP using the **Service Layer API** (REST-based).

```python
# Example from your project
class SAPClient:
    def __init__(self, company_db_key='4B-BIO'):
        self.base_url = os.getenv('SAP_B1S_HOST')
        self.company_db = company_db_key
        self.session_id = None
        
    def login(self):
        """Authenticate with SAP Service Layer"""
        response = requests.post(
            f"{self.base_url}/Login",
            json={
                "CompanyDB": self.company_db,
                "UserName": os.getenv('SAP_USER'),
                "Password": os.getenv('SAP_PASSWORD')
            }
        )
        self.session_id = response.cookies.get('B1SESSION')
        
    def create_sales_order(self, order_data):
        """POST sales order to SAP"""
        return requests.post(
            f"{self.base_url}/Orders",
            json=order_data,
            cookies={'B1SESSION': self.session_id}
        )
```

### Key SAP Concepts

#### Business Partners (BP)
- **CardCode**: Unique customer/vendor identifier (e.g., `BIC01563`)
- **CardName**: Business partner name
- **ContactPersonCode**: Contact person ID

#### Sales Orders
- **DocEntry**: Document entry number (unique ID)
- **DocNum**: Document number (user-facing)
- **DocumentLines**: Line items in the order

#### Projects & Policies
- **ProjectCode**: SAP project identifier (e.g., `0223254`)
- **U_policy**: Custom field for policy number

**Interview Question**: "What is the difference between DocEntry and DocNum?"
- **DocEntry**: Internal system ID (auto-generated, never changes)
- **DocNum**: User-visible document number (can be customized per series)

---

## 2. **SAP HANA Database**

### What is HANA?
SAP HANA is an **in-memory database** optimized for real-time analytics and transactions.

### HANA Connection (hdbcli)
```python
from hdbcli import dbapi

# Connect to HANA
conn = dbapi.connect(
    address='your-hana-host',
    port=30015,
    user='HANA_USER',
    password='HANA_PASSWORD',
    encrypt=True
)

# Set schema (multi-tenant)
cursor = conn.cursor()
cursor.execute('SET SCHEMA "4B-BIO_APP"')

# Query data
cursor.execute('SELECT * FROM OITM WHERE "ItemCode" = ?', ['FG00581'])
results = cursor.fetchall()
```

### Multi-Schema Architecture
Your project supports **multiple company databases** (schemas):
- `4B-BIO_APP` - Bio division
- `4B-ORANG_APP` - Orange division
- `4B-AGRI_APP` - Agriculture division

### Key HANA Tables
| Table | Purpose |
|-------|---------|
| OITM | Item Master (Products) |
| OCRD | Business Partners (Customers/Vendors) |
| ORDR | Sales Orders |
| OPRJ | Projects |
| OTER | Territories |
| @ODID | User-Defined Table (Disease Identification) |

**Interview Question**: "What is the difference between in-memory and traditional databases?"
- **In-memory**: Data stored in RAM (faster, real-time analytics)
- **Traditional**: Data stored on disk (slower, batch processing)

---

## 3. **drf-yasg (Swagger/OpenAPI Documentation)**

### What is drf-yasg?
**Yet Another Swagger Generator** - Automatically generates API documentation for Django REST Framework.

### Usage in Your Project
```python
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

@swagger_auto_schema(
    method='get',
    operation_description="Get policy customer balance",
    parameters=[
        openapi.Parameter(
            'database',
            openapi.IN_QUERY,
            description="Database/Company schema",
            type=openapi.TYPE_STRING,
            required=True
        ),
        openapi.Parameter(
            'card_code',
            openapi.IN_QUERY,
            description="Customer CardCode",
            type=openapi.TYPE_STRING,
            required=False
        )
    ],
    responses={
        200: "Success",
        400: "Bad Request",
        500: "Server Error"
    }
)
@api_view(['GET'])
def policy_customer_balance_api(request):
    database = request.GET.get('database')
    card_code = request.GET.get('card_code')
    # Your logic here
```

### Swagger Settings
```python
# settings.py
SWAGGER_SETTINGS = {
    'USE_SESSION_AUTH': False,
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header'
        }
    },
    'DEFAULT_AUTO_SCHEMA_CLASS': 'web_portal.swagger.CustomAutoSchema',
}
```

**Access Swagger UI**: `http://localhost:8000/swagger/`

---

## 4. **JWT Authentication (SimpleJWT)**

### What is JWT?
**JSON Web Token** - Stateless authentication mechanism.

### JWT Structure
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJleHAiOjE2MzI0NTY3ODl9.signature
│                                      │                                        │
└─────────── Header ───────────────────┴────────── Payload ────────────────────┴─ Signature
```

### Configuration in Your Project
```python
# settings.py
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}
```

### Usage
```python
# Login endpoint
from rest_framework_simplejwt.tokens import RefreshToken

def login(request):
    user = authenticate(email=email, password=password)
    refresh = RefreshToken.for_user(user)
    return Response({
        'access': str(refresh.access_token),
        'refresh': str(refresh)
    })

# Protected endpoint
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def protected_view(request):
    user = request.user  # Authenticated user
    return Response({'message': f'Hello {user.email}'})
```

**Interview Question**: "Why use JWT over session-based authentication?"
- **Stateless**: No server-side session storage
- **Scalable**: Works across multiple servers
- **Mobile-friendly**: Easy to use in mobile apps
- **Cross-domain**: Can be used across different domains

---

## 5. **Custom User Model & Authentication**

### Custom User Model
```python
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin

class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    profile_image = models.ImageField(upload_to='profile_images/')
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True)
    is_sales_staff = models.BooleanField(default=False)
    is_dealer = models.BooleanField(default=False)
    
    USERNAME_FIELD = 'email'  # Login with email
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']
```

### Custom Authentication Backend
```python
# accounts/backends.py
from django.contrib.auth.backends import ModelBackend

class EmailOrPhoneBackend(ModelBackend):
    """Allow login with email OR phone number"""
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # Try email first
            user = User.objects.get(email=username)
        except User.DoesNotExist:
            try:
                # Try phone number
                user = User.objects.get(
                    sales_profile__phone_number=username
                )
            except User.DoesNotExist:
                return None
        
        if user.check_password(password):
            return user
        return None
```

**Why Custom User Model?**
- Add custom fields (role, profile_image, etc.)
- Use email instead of username for login
- Better control over user management

---

## 6. **Role-Based Access Control (RBAC)**

### Role Model
```python
class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)
    permissions = models.ManyToManyField(Permission, blank=True)
```

### Custom Permissions
```python
class Meta:
    permissions = [
        ('manage_users', 'Can add/edit users'),
        ('view_organogram', 'Can view organization hierarchy'),
        ('access_hana_connect', 'Can access HANA Connect dashboard'),
        ('post_to_sap', 'Can post data to SAP'),
        ('view_sales_orders', 'Can view Sales Orders'),
    ]
```

### Permission Checking
```python
# In views
from rest_framework.permissions import BasePermission

class HasSAPPostPermission(BasePermission):
    def has_permission(self, request, view):
        return request.user.has_perm('sap_integration.post_to_sap')

@api_view(['POST'])
@permission_classes([IsAuthenticated, HasSAPPostPermission])
def create_sales_order(request):
    # Only users with 'post_to_sap' permission can access
    pass

# In templates
{% if perms.sap_integration.view_sales_orders %}
    <a href="/sales-orders/">View Orders</a>
{% endif %}
```

**Interview Question**: "What is the difference between authentication and authorization?"
- **Authentication**: Who are you? (Login)
- **Authorization**: What can you do? (Permissions)

---

## 7. **Django Filters & Pagination**

### Django Filters
```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.OrderingFilter',
    ],
}

# In views
from django_filters import rest_framework as filters

class PolicyFilter(filters.FilterSet):
    active = filters.BooleanFilter()
    valid_from = filters.DateFilter(field_name='valid_from', lookup_expr='gte')
    
    class Meta:
        model = Policy
        fields = ['active', 'code', 'valid_from']

# Usage: /api/policies/?active=true&code=POL001
```

### Pagination
```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
}

# Custom pagination
from rest_framework.pagination import PageNumberPagination

class LargeResultsSetPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000

# Usage: /api/policies/?page=2&page_size=50
```

---

## 8. **CORS (Cross-Origin Resource Sharing)**

### Why CORS?
Your Django backend runs on `localhost:8000`, but your frontend (React/Next.js) runs on `localhost:3000`. Browsers block cross-origin requests by default.

### Configuration
```python
# settings.py
INSTALLED_APPS = [
    'corsheaders',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # Must be at top
    'django.middleware.common.CommonMiddleware',
]

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://192.168.18.209:3000",
]

CORS_ALLOW_CREDENTIALS = True  # Allow cookies
```

**Interview Question**: "What is a preflight request?"
- Browser sends `OPTIONS` request before actual request
- Checks if server allows the cross-origin request
- If allowed, browser sends the actual request

---

## 9. **Environment Variables (.env)**

### Why Use .env Files?
- **Security**: Keep secrets out of source code
- **Flexibility**: Different configs for dev/staging/prod
- **Team collaboration**: Each developer has their own .env

### python-decouple
```python
# .env file
DB_NAME=agrigenie
DB_USER=root
DB_PASSWORD=samad
SAP_B1S_HOST=https://sap-server:50000/b1s/v1
HANA_HOST=hana-server
HANA_PASSWORD=secret

# settings.py
from decouple import Config, RepositoryEnv

ENV_FILE = BASE_DIR.parent / '.env'
config = Config(RepositoryEnv(str(ENV_FILE)))

DATABASES = {
    'default': {
        'NAME': config('DB_NAME', default='agrigenie'),
        'USER': config('DB_USER', default='root'),
        'PASSWORD': config('DB_PASSWORD'),
    }
}
```

**Security Best Practice**: Add `.env` to `.gitignore`!

---

## 10. **MySQL Database**

### Configuration
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'agrigenie',
        'USER': 'root',
        'PASSWORD': 'samad',
        'HOST': '127.0.0.1',
        'PORT': '3306',
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset': 'utf8mb4',
        },
        'CONN_MAX_AGE': 600,  # Connection pooling
    }
}
```

### Connection Pooling
- **CONN_MAX_AGE**: Keep connections alive for 10 minutes
- **Benefit**: Reduces overhead of creating new connections
- **Trade-off**: Uses more memory

---

## 11. **Celery (Async Task Queue)**

### What is Celery?
Distributed task queue for running background jobs.

### Use Cases
- Sending emails
- Generating reports
- Syncing data from SAP
- Image processing

### Configuration
```python
# celery.py
from celery import Celery

app = Celery('web_portal')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# tasks.py
from celery import shared_task

@shared_task
def sync_sap_policies():
    """Background task to sync policies from SAP"""
    client = SAPClient()
    policies = client.get_policies()
    # Save to database
    return f"Synced {len(policies)} policies"

# Usage
sync_sap_policies.delay()  # Run async
```

### Message Broker
- **Redis**: Fast, in-memory (used in your project)
- **RabbitMQ**: More features, persistent

---

## 12. **Django Signals**

### What are Signals?
Event-driven notifications when certain actions occur.

### Common Signals
```python
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Auto-create profile when user is created"""
    if created:
        SalesStaffProfile.objects.create(user=instance)

@receiver(pre_delete, sender=SalesStaffProfile)
def unmark_sales_staff(sender, instance, **kwargs):
    """Unmark user as sales staff when profile is deleted"""
    if instance.user:
        instance.user.is_sales_staff = False
        instance.user.save()
```

---

## 13. **File Upload & Media Handling**

### Configuration
```python
# settings.py
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# urls.py (for development)
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Your URLs
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

### Image Validation
```python
from django.core.validators import FileExtensionValidator

def validate_image_size(image):
    max_size_mb = 2
    if image.size > max_size_mb * 1024 * 1024:
        raise ValidationError(f"Image too large (> {max_size_mb}MB)")

class User(models.Model):
    profile_image = models.ImageField(
        upload_to='profile_images/',
        validators=[
            FileExtensionValidator(['jpg', 'jpeg', 'png']),
            validate_image_size,
        ]
    )
```

### Pillow Library
- Required for `ImageField`
- Image processing and manipulation

---

## 14. **Logging & Debugging**

### Configuration
```python
# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} - {name} - {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'hana': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
    },
}
```

### Usage
```python
import logging

logger = logging.getLogger('hana')

def get_hana_data():
    logger.info("Connecting to HANA database")
    try:
        # Your code
        logger.debug(f"Query returned {len(results)} rows")
    except Exception as e:
        logger.error(f"HANA query failed: {str(e)}")
```

---

## 15. **Django Admin Customization**

### Custom Admin Site
```python
# admin.py
from django.contrib import admin

admin.site.site_header = "Agrigenie Tech"
admin.site.site_title = "Agrigenie Tech"
admin.site.index_title = "Welcome to Agrigenie Tech Portal"

@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'active', 'valid_from', 'valid_to']
    list_filter = ['active', 'valid_from']
    search_fields = ['code', 'name', 'policy']
    readonly_fields = ['created_at', 'updated_at']
```

### Staff Member Required Decorator
```python
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def sales_order_admin(request):
    """Custom admin view for creating sales orders"""
    # Only accessible to staff members
    pass
```

---

## 16. **Many-to-Many Relationships**

### Example from Your Project
```python
class SalesStaffProfile(models.Model):
    # One staff member can be assigned to multiple territories
    territories = models.ManyToManyField(
        'FieldAdvisoryService.Territory',
        blank=True,
        related_name="sales_profiles"
    )
    
    # Multiple companies
    companies = models.ManyToManyField(
        'FieldAdvisoryService.Company',
        blank=True,
        related_name="sales_profiles"
    )
```

### Querying M2M
```python
# Get all territories for a staff member
staff = SalesStaffProfile.objects.get(id=1)
territories = staff.territories.all()

# Get all staff members in a territory
territory = Territory.objects.get(name='Lahore')
staff_in_territory = territory.sales_profiles.all()

# Filter by M2M
staff_in_lahore = SalesStaffProfile.objects.filter(
    territories__name='Lahore'
)
```

---

## 17. **Self-Referencing Foreign Keys (Hierarchies)**

### Organizational Hierarchy
```python
class SalesStaffProfile(models.Model):
    # Self-referencing FK for manager-subordinate
    manager = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subordinates'
    )
    
    def get_all_subordinates(self):
        """Recursively get all subordinates"""
        subordinate_ids = set()
        
        def _collect(manager_id):
            direct_subs = SalesStaffProfile.objects.filter(
                manager_id=manager_id
            ).values_list('id', flat=True)
            
            for sub_id in direct_subs:
                if sub_id not in subordinate_ids:
                    subordinate_ids.add(sub_id)
                    _collect(sub_id)  # Recursive
        
        _collect(self.id)
        return SalesStaffProfile.objects.filter(id__in=subordinate_ids)
```

---

## 18. **Django Serializers (DRF)**

### ModelSerializer
```python
from rest_framework import serializers

class PolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = Policy
        fields = ['id', 'code', 'name', 'active', 'valid_from', 'valid_to']
        read_only_fields = ['id', 'created_at', 'updated_at']
```

### Custom Validation
```python
class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    
    def validate_email(self, value):
        """Custom email validation"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value
    
    def create(self, validated_data):
        """Override create to hash password"""
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user
```

---

## 19. **Context Processors**

### Custom Context Processor
```python
# sap_integration/context_processors.py
def db_selector(request):
    """Make database options available in all templates"""
    companies = Company.objects.filter(is_active=True)
    return {
        'available_databases': companies,
        'selected_db': request.session.get('selected_db', '4B-BIO')
    }

# settings.py
TEMPLATES = [{
    'OPTIONS': {
        'context_processors': [
            'sap_integration.context_processors.db_selector',
        ],
    },
}]
```

---

## 20. **API Versioning Strategies**

### URL Path Versioning
```python
# urls.py
urlpatterns = [
    path('api/v1/policies/', views.policies_v1),
    path('api/v2/policies/', views.policies_v2),
]
```

### Header Versioning
```python
# Custom middleware
class APIVersionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        version = request.META.get('HTTP_API_VERSION', 'v1')
        request.api_version = version
        return self.get_response(request)
```

---

## Key Interview Topics from This Project

### 1. **ERP Integration**
- How to integrate with third-party systems (SAP)
- Session management with external APIs
- Error handling for external API calls

### 2. **Multi-Tenancy**
- Multiple company schemas in HANA
- Dynamic schema switching
- Data isolation between tenants

### 3. **Complex Permissions**
- Role-based access control
- Object-level permissions
- Hierarchical permissions (manager can see subordinate data)

### 4. **Performance Optimization**
- Database connection pooling
- Caching strategies
- N+1 query prevention

### 5. **Security**
- JWT authentication
- Password hashing
- SQL injection prevention
- CORS configuration
- Environment variable management

---

## Common Interview Questions for This Stack

**Q: How do you handle SAP session timeouts?**
```python
def ensure_sap_session(self):
    """Re-login if session expired"""
    try:
        # Test session
        response = requests.get(
            f"{self.base_url}/test",
            cookies={'B1SESSION': self.session_id}
        )
        if response.status_code == 401:
            self.login()  # Re-authenticate
    except Exception:
        self.login()
```

**Q: How do you prevent N+1 queries in Django?**
```python
# BAD - N+1 query
staff_members = SalesStaffProfile.objects.all()
for staff in staff_members:
    print(staff.user.email)  # Hits DB each time

# GOOD - Use select_related
staff_members = SalesStaffProfile.objects.select_related('user').all()
for staff in staff_members:
    print(staff.user.email)  # No additional queries
```

---

## Additional Backend Terms Used in This Project

### 21. **ViewSets (DRF)**

#### What are ViewSets?
ViewSets combine the logic for multiple related views (list, create, retrieve, update, delete) into a single class.

#### Benefits
- **Less code**: One class instead of multiple views
- **Automatic routing**: Router generates URL patterns
- **Consistent API**: Standard CRUD operations

#### ModelViewSet Example from Your Project

```python
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .permissions import HasRolePermission

class RoleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Role CRUD operations
    Provides: list, create, retrieve, update, partial_update, destroy
    """
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id', 'name']
    
    # Automatic endpoints:
    # GET    /api/roles/          → list()
    # POST   /api/roles/          → create()
    # GET    /api/roles/{id}/     → retrieve()
    # PUT    /api/roles/{id}/     → update()
    # PATCH  /api/roles/{id}/     → partial_update()
    # DELETE /api/roles/{id}/     → destroy()
```

#### Custom Actions with @action Decorator

```python
from rest_framework.decorators import action
from rest_framework.response import Response

class RoleViewSet(viewsets.ModelViewSet):
    # ... (same as above)
    
    @action(detail=True, methods=['get'], url_path='permissions')
    def permissions_list(self, request, pk=None):
        """
        Custom endpoint: GET /api/roles/{id}/permissions/
        Returns all permissions for a specific role
        """
        role = self.get_object()
        permissions = role.permissions.all()
        serializer = PermissionSerializer(permissions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], url_path='bulk-create')
    def bulk_create(self, request):
        """
        Custom endpoint: POST /api/roles/bulk-create/
        Create multiple roles at once
        """
        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
```

**Interview Question**: "What's the difference between `detail=True` and `detail=False` in @action?"
- **`detail=True`**: Requires an ID, URL pattern: `/api/resource/{id}/action/`
- **`detail=False`**: No ID needed, URL pattern: `/api/resource/action/`

### 22. **Custom Permissions**

#### Built-in DRF Permissions
```python
from rest_framework.permissions import (
    AllowAny,           # No authentication required
    IsAuthenticated,    # Must be logged in
    IsAdminUser,        # Must be staff/admin
    IsAuthenticatedOrReadOnly,  # Read-only for anonymous
)
```

#### Custom Permission Classes from Your Project

```python
from rest_framework.permissions import BasePermission

class HasRolePermission(BasePermission):
    """
    Check if user has required permission based on their role
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Superusers bypass all checks
        if request.user.is_superuser:
            return True
        
        # Check if user's role has the required permission
        required_permission = getattr(view, 'required_permission', None)
        if required_permission:
            return request.user.has_perm(required_permission)
        
        return True

class IsOwnerOrAdmin(BasePermission):
    """
    Allow access only to object owner or admin users
    """
    def has_object_permission(self, request, view, obj):
        # Admin can access everything
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # Owner can access their own object
        return obj.user == request.user

class CanAddToCart(BasePermission):
    """
    Custom permission for cart operations
    """
    def has_permission(self, request, view):
        return request.user.has_perm('cart.add_cartitem')

class CanViewOrderHistory(BasePermission):
    """
    Permission to view order history
    """
    def has_permission(self, request, view):
        return request.user.has_perm('cart.view_order')
```

#### Using Multiple Permissions

```python
from rest_framework import viewsets

class CartViewSet(viewsets.ModelViewSet):
    queryset = Cart.objects.all()
    serializer_class = CartSerializer
    
    # Multiple permissions - ALL must pass
    permission_classes = [IsAuthenticated, CanAddToCart]
    
    @action(detail=False, methods=['post'], 
            permission_classes=[IsAuthenticated, CanAddToCart])
    def add_item(self, request):
        """Different permissions for specific actions"""
        # Your logic here
        pass
```

### 23. **Error Handling & Exception Handling**

#### Try-Except Patterns from Your Project

```python
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)

@api_view(['GET'])
def get_hana_data(request):
    """Robust error handling for external system integration"""
    try:
        # Get database parameter
        database = request.GET.get('database')
        if not database:
            return Response(
                {'error': 'Database parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Connect to HANA
        conn = get_hana_connection(database)
        
        # Execute query
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM OITM WHERE "ItemCode" = ?', ['FG00581'])
        results = cursor.fetchall()
        
        return Response({
            'success': True,
            'data': results
        }, status=status.HTTP_200_OK)
        
    except ConnectionError as e:
        logger.error(f"HANA connection failed: {e}")
        return Response(
            {'error': 'Database connection failed', 'details': str(e)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    
    except ValueError as e:
        logger.warning(f"Invalid data: {e}")
        return Response(
            {'error': 'Invalid data provided', 'details': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return Response(
            {'error': 'Internal server error', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    finally:
        # Always close connection
        if 'conn' in locals() and conn:
            conn.close()
```

#### Custom Exception Classes

```python
from rest_framework.exceptions import APIException

class SAPConnectionError(APIException):
    status_code = 503
    default_detail = 'SAP service temporarily unavailable.'
    default_code = 'sap_unavailable'

class HANAQueryError(APIException):
    status_code = 500
    default_detail = 'HANA database query failed.'
    default_code = 'hana_query_error'

# Usage
def query_sap_data():
    try:
        # SAP logic
        pass
    except requests.exceptions.ConnectionError:
        raise SAPConnectionError('Unable to connect to SAP Service Layer')
```

#### Validation Errors

```python
from rest_framework import serializers

class UserSerializer(serializers.ModelSerializer):
    def validate_email(self, value):
        """Field-level validation"""
        if not value.endswith('@company.com'):
            raise serializers.ValidationError(
                "Must use company email address"
            )
        return value
    
    def validate(self, data):
        """Object-level validation"""
        if data.get('is_sales_staff') and not data.get('employee_code'):
            raise serializers.ValidationError({
                'employee_code': 'Employee code is required for sales staff'
            })
        return data
```

### 24. **Database Transactions**

#### @transaction.atomic Decorator

```python
from django.db import transaction

@transaction.atomic
def create_order_with_items(request):
    """
    All operations succeed or all fail (rollback)
    Ensures data consistency
    """
    # Create order
    order = Order.objects.create(
        user=request.user,
        total_amount=0
    )
    
    # Add items
    total = 0
    for item_data in request.data['items']:
        item = OrderItem.objects.create(
            order=order,
            product_id=item_data['product_id'],
            quantity=item_data['quantity'],
            price=item_data['price']
        )
        total += item.quantity * item.price
    
    # Update total
    order.total_amount = total
    order.save()
    
    # If any exception occurs, ALL changes are rolled back
    return order
```

#### Context Manager for Transactions

```python
from django.db import transaction

def transfer_funds(from_account, to_account, amount):
    """Manual transaction control"""
    try:
        with transaction.atomic():
            # Deduct from source
            from_account.balance -= amount
            from_account.save()
            
            # Simulate error
            if amount > 10000:
                raise ValueError("Amount too large")
            
            # Add to destination
            to_account.balance += amount
            to_account.save()
            
    except ValueError as e:
        # Transaction automatically rolled back
        logger.error(f"Transfer failed: {e}")
        raise
```

#### Savepoints for Partial Rollback

```python
from django.db import transaction

@transaction.atomic
def complex_operation():
    # Create user
    user = User.objects.create(username='john')
    
    # Create savepoint
    sid = transaction.savepoint()
    
    try:
        # Risky operation
        profile = SalesStaffProfile.objects.create(user=user)
    except Exception:
        # Rollback to savepoint (user still created)
        transaction.savepoint_rollback(sid)
    else:
        # Commit savepoint
        transaction.savepoint_commit(sid)
```

**Interview Question**: "When should you use transactions?"
- **Financial operations**: Money transfers, payments
- **Multi-step operations**: Creating related objects
- **Data consistency**: Ensuring referential integrity
- **Batch operations**: All-or-nothing bulk updates

### 25. **Decorators in Django**

#### Common DRF Decorators

```python
from rest_framework.decorators import (
    api_view,
    permission_classes,
    authentication_classes,
    throttle_classes,
    action
)

# Function-based view
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def my_api_view(request):
    if request.method == 'GET':
        return Response({'message': 'GET request'})
    else:
        return Response({'message': 'POST request'})

# Custom throttling
from rest_framework.throttling import UserRateThrottle

@api_view(['POST'])
@throttle_classes([UserRateThrottle])
def rate_limited_endpoint(request):
    """Limited to 100 requests per hour"""
    return Response({'status': 'success'})
```

#### Swagger/OpenAPI Decorators

```python
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

@swagger_auto_schema(
    method='get',
    operation_description="Get user territories",
    manual_parameters=[
        openapi.Parameter(
            'user_id',
            openapi.IN_PATH,
            description='User ID',
            type=openapi.TYPE_INTEGER,
            required=True
        ),
        openapi.Parameter(
            'database',
            openapi.IN_QUERY,
            description='Database name',
            type=openapi.TYPE_STRING,
            required=False
        )
    ],
    responses={
        200: openapi.Response(description="Success"),
        404: openapi.Response(description="User not found"),
        403: openapi.Response(description="Forbidden")
    },
    tags=["User Management"]
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_territories_api(request, user_id):
    # Your logic here
    pass
```

#### Django Built-in Decorators

```python
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_http_methods

@login_required
@permission_required('accounts.view_user', raise_exception=True)
def admin_dashboard(request):
    """Only logged-in users with permission can access"""
    return render(request, 'admin_dashboard.html')

@cache_page(60 * 15)  # Cache for 15 minutes
def cached_view(request):
    """Response is cached"""
    expensive_data = perform_expensive_query()
    return render(request, 'template.html', {'data': expensive_data})

@require_http_methods(["GET", "POST"])
def my_view(request):
    """Only GET and POST allowed, others return 405"""
    pass
```

### 26. **Query Optimization Techniques**

#### only() - Fetch Specific Fields

```python
# BAD - Fetches all fields
users = User.objects.all()

# GOOD - Only fetch needed fields
users = User.objects.only('id', 'email', 'username')

# Reduces memory and database load
for user in users:
    print(user.email)  # OK
    print(user.first_name)  # Causes additional query!
```

#### defer() - Exclude Specific Fields

```python
# Fetch all fields EXCEPT large ones
users = User.objects.defer('profile_image', 'bio')

# Useful for excluding BLOBs or large text fields
```

#### values() and values_list()

```python
# Returns dictionaries
emails = User.objects.values('id', 'email')
# [{'id': 1, 'email': 'user@example.com'}, ...]

# Returns tuples
emails = User.objects.values_list('email', flat=True)
# ['user1@example.com', 'user2@example.com', ...]

# Faster than model instances for simple data extraction
```

#### Aggregation and Annotation

```python
from django.db.models import Count, Sum, Avg, Max, Min

# Count related objects
users_with_order_count = User.objects.annotate(
    order_count=Count('orders')
).filter(order_count__gt=5)

# Calculate totals
from cart.models import Order

order_totals = Order.objects.aggregate(
    total_revenue=Sum('total_amount'),
    avg_order_value=Avg('total_amount'),
    max_order=Max('total_amount')
)
# {'total_revenue': 150000, 'avg_order_value': 1500, 'max_order': 25000}

# Annotate each object
orders = Order.objects.annotate(
    item_count=Count('items')
).filter(item_count__gt=3)
```

#### Bulk Operations

```python
# BAD - N queries
for user in users:
    user.is_active = True
    user.save()  # 1 query per user

# GOOD - 1 query
User.objects.filter(id__in=user_ids).update(is_active=True)

# Bulk create
users = [
    User(username=f'user{i}', email=f'user{i}@example.com')
    for i in range(1000)
]
User.objects.bulk_create(users)  # Single query

# Bulk update (Django 4.2+)
users = User.objects.all()
for user in users:
    user.is_active = True
User.objects.bulk_update(users, ['is_active'])
```

### 27. **Context in Serializers**

#### Passing Context to Serializers

```python
# In your view
def get_disease_details(request, disease_id):
    disease = DiseaseIdentification.objects.get(id=disease_id)
    
    # Fetch product catalog from HANA
    product_catalog = fetch_product_catalog_from_hana()
    
    # Pass as context
    serializer = DiseaseIdentificationSerializer(
        disease,
        context={
            'request': request,
            'product_catalog': product_catalog,
            'user': request.user
        }
    )
    
    return Response(serializer.data)
```

#### Using Context in Serializer

```python
class RecommendedProductSerializer(serializers.ModelSerializer):
    product_image_url = serializers.SerializerMethodField()
    
    def get_product_image_url(self, obj):
        """Access context data"""
        # Get product catalog from context
        product_catalog = self.context.get('product_catalog', {})
        product = product_catalog.get(obj.product_item_code, {})
        return product.get('product_image_url')
    
    def get_current_user(self):
        """Access request user from context"""
        request = self.context.get('request')
        return request.user if request else None
```

### 28. **Filtering and Searching**

#### Django Filter Backend

```python
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    
    # Exact match filtering
    filterset_fields = ['is_active', 'role', 'is_sales_staff']
    
    # Full-text search
    search_fields = ['username', 'email', 'first_name', 'last_name']
    
    # Ordering
    ordering_fields = ['id', 'email', 'date_joined']
    ordering = ['-date_joined']  # Default ordering

# Usage:
# /api/users/?is_active=true&role=5
# /api/users/?search=john
# /api/users/?ordering=-date_joined
```

#### Custom FilterSet

```python
import django_filters
from .models import Policy

class PolicyFilter(django_filters.FilterSet):
    # Custom filters
    name = django_filters.CharFilter(lookup_expr='icontains')
    active = django_filters.BooleanFilter()
    valid_from = django_filters.DateFilter(lookup_expr='gte')
    valid_to = django_filters.DateFilter(lookup_expr='lte')
    
    # Range filter
    created_at = django_filters.DateFromToRangeFilter()
    
    class Meta:
        model = Policy
        fields = ['name', 'active', 'valid_from', 'valid_to', 'created_at']

# In ViewSet
class PolicyViewSet(viewsets.ModelViewSet):
    queryset = Policy.objects.all()
    serializer_class = PolicySerializer
    filterset_class = PolicyFilter

# Usage:
# /api/policies/?name=crop&active=true
# /api/policies/?valid_from=2024-01-01&valid_to=2024-12-31
# /api/policies/?created_at_after=2024-01-01&created_at_before=2024-12-31
```

### 29. **File Upload Handling**

#### Image Upload with Validation

```python
from django.core.validators import FileExtensionValidator
from PIL import Image

class User(AbstractBaseUser):
    profile_image = models.ImageField(
        upload_to='profile_images/',
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png']),
        ],
        null=True,
        blank=True
    )
    
    def save(self, *args, **kwargs):
        """Validate image size before saving"""
        if self.profile_image:
            img = Image.open(self.profile_image)
            
            # Check dimensions
            if img.width > 2000 or img.height > 2000:
                raise ValidationError('Image dimensions too large (max 2000x2000)')
            
            # Check file size
            if self.profile_image.size > 5 * 1024 * 1024:  # 5MB
                raise ValidationError('Image file too large (max 5MB)')
        
        super().save(*args, **kwargs)
```

#### Handling File Uploads in API

```python
from rest_framework.parsers import MultiPartParser, FormParser

class UserSignupView(generics.CreateAPIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def post(self, request, *args, **kwargs):
        # Access uploaded file
        profile_image = request.FILES.get('profile_image')
        
        if profile_image:
            # Validate file type
            if not profile_image.content_type.startswith('image/'):
                return Response(
                    {'error': 'File must be an image'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return super().post(request, *args, **kwargs)
```

### 30. **Logging Best Practices**

#### Logger Configuration (from your project)

```python
import logging

# Get logger for current module
logger = logging.getLogger(__name__)

@api_view(['GET'])
def get_hana_data(request):
    database = request.GET.get('database')
    
    # Info level - normal operations
    logger.info(f"Fetching data from HANA database: {database}")
    
    try:
        conn = get_hana_connection(database)
        logger.debug(f"Connection established: {conn}")
        
        # Your logic
        result = fetch_data(conn)
        
        logger.info(f"Successfully fetched {len(result)} records")
        return Response({'data': result})
        
    except ConnectionError as e:
        # Error level - something went wrong
        logger.error(f"HANA connection failed for {database}: {e}")
        return Response({'error': str(e)}, status=500)
        
    except Exception as e:
        # Exception level - unexpected errors with stack trace
        logger.exception(f"Unexpected error in get_hana_data: {e}")
        return Response({'error': 'Internal server error'}, status=500)
```

#### Logging Levels

```python
logger.debug("Detailed diagnostic information")      # Development only
logger.info("General informational messages")        # Normal operations
logger.warning("Warning messages")                   # Potential issues
logger.error("Error messages")                       # Errors occurred
logger.critical("Critical errors")                   # System failures
logger.exception("Error with stack trace")           # In except blocks
```

---

## Interview Questions Specific to This Project

**Q: How do you prevent N+1 queries when fetching user territories?**
```python
# From your project - accounts/views.py
profile = (
    SalesStaffProfile.objects
    .select_related('user')  # ForeignKey
    .prefetch_related(
        'companies',
        'regions__company',
        'zones__region__company',
        'territories__zone__region__company'  # Nested prefetch
    )
    .get(user_id=user_id)
)
```

**Q: How do you handle SAP session timeouts?**
```python
class SAPClient:
    def __init__(self):
        self.session_id = None
        self.session_timeout = 30 * 60  # 30 minutes
        self.last_request_time = None
    
    def _ensure_session(self):
        """Re-login if session expired"""
        now = time.time()
        if (not self.session_id or 
            not self.last_request_time or 
            now - self.last_request_time > self.session_timeout):
            self.login()
        self.last_request_time = now
    
    def get_data(self, endpoint):
        self._ensure_session()
        # Make request with session
```

**Q: How do you handle database transactions?**
```python
from django.db import transaction

@transaction.atomic
def create_order_with_items(order_data, items):
    """All or nothing - rollback if any fails"""
    order = Order.objects.create(**order_data)
    for item in items:
        OrderItem.objects.create(order=order, **item)
    return order
```

---

## Conclusion

This project demonstrates real-world enterprise application development with:
- **External integrations** (SAP, HANA)
- **Complex authentication** (JWT, custom backends)
- **Advanced permissions** (RBAC, hierarchical)
- **API documentation** (Swagger/OpenAPI)
- **Performance optimization** (caching, connection pooling)
- **Security best practices** (environment variables, validation)

Understanding these concepts will make you a strong backend developer ready for enterprise-level projects!

# DRF Decorators & Important Imports Guide
> **Project:** Django Web Portal  
> **Purpose:** Explain every important DRF decorator and import used in this project with real code examples

---

## Table of Contents

1. [`from rest_framework.decorators import action`](#1-action-decorator)
2. [`from rest_framework.decorators import api_view`](#2-api_view-decorator)
3. [`from rest_framework.decorators import permission_classes`](#3-permission_classes-decorator)
4. [`from rest_framework.decorators import parser_classes`](#4-parser_classes-decorator)
5. [`from rest_framework.response import Response`](#5-response)
6. [`from rest_framework import viewsets, status`](#6-viewsets--status)
7. [`from rest_framework.permissions import IsAuthenticated`](#7-isAuthenticated--other-permissions)
8. [`from rest_framework.parsers import MultiPartParser, FormParser`](#8-parsers)
9. [`from rest_framework.filters import SearchFilter, OrderingFilter`](#9-searchfilter--orderingfilter)
10. [`from rest_framework.pagination import PageNumberPagination`](#10-pagenumberpagination)
11. [`from drf_yasg.utils import swagger_auto_schema`](#11-swagger_auto_schema)
12. [`from drf_yasg import openapi`](#12-openapi)
13. [`from django.db import transaction`](#13-transactionatomic)
14. [`from django_filters.rest_framework import DjangoFilterBackend`](#14-djangofilterbackend)
15. [`from rest_framework.views import APIView`](#15-apiview)

---

## 1. `@action` Decorator

### What is it?
`@action` is used inside a **ViewSet** to add **custom endpoints** beyond the standard CRUD operations.

### Import
```python
from rest_framework.decorators import action
```

### Syntax
```python
@action(detail=True/False, methods=['get', 'post', ...], url_path='custom-url', permission_classes=[...])
def my_custom_action(self, request, pk=None):
    ...
```

### Key Parameters

| Parameter | What it does | Example |
|-----------|-------------|---------|
| `detail=True` | Requires an object ID in URL | `/api/users/{id}/my-team/` |
| `detail=False` | No ID needed, collection-level | `/api/cart/add-item/` |
| `methods` | HTTP methods allowed | `['get']`, `['post']`, `['patch', 'delete']` |
| `url_path` | Custom URL segment | `url_path='my-team'` → `/my-team/` |
| `permission_classes` | Override permissions for this action only | `[IsAuthenticated, CanAddToCart]` |

---

### Real Examples from This Project

#### Example 1 — `cart/views.py`: Add item to cart
```python
@swagger_auto_schema(
    operation_description="Add product to cart (requires add_to_cart permission)",
    request_body=AddToCartSerializer,
    tags=["06. Shopping Cart"]
)
@action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, CanAddToCart])
def add_item(self, request):
    """Add item to cart"""
    serializer = AddToCartSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    cart_id = serializer.validated_data['cart_id']
    user_id = serializer.validated_data['user_id']

    cart = get_object_or_404(Cart, id=cart_id, user_id=user_id)

    # Security check
    if not request.user.is_superuser and cart.user != request.user:
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

    # Create cart item
    cart_item = CartItem.objects.create(
        cart=cart,
        product_item_code=serializer.validated_data['product_item_code'],
        quantity=serializer.validated_data.get('quantity', 1),
    )
    return Response({'message': 'Item added to cart'}, status=status.HTTP_201_CREATED)
```
> **URL generated:** `POST /api/cart/add-item/`

---

#### Example 2 — `cart/views.py`: Update item with custom URL pattern
```python
@action(detail=False, methods=['patch'], url_path='update-item/(?P<item_id>[^/.]+)')
def update_item(self, request, item_id=None):
    """Update cart item quantity — custom URL captures item_id"""
    cart_item = get_object_or_404(CartItem, id=item_id)
    serializer = UpdateCartItemSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    cart_item.quantity = serializer.validated_data['quantity']
    cart_item.save()
    return Response({'message': 'Cart item updated'})
```
> **URL generated:** `PATCH /api/cart/update-item/{item_id}/`  
> **Note:** `url_path` uses a **regex** to capture `item_id` from the URL.

---

#### Example 3 — `cart/views.py`: Checkout with `@transaction.atomic`
```python
@transaction.atomic
@action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, CanAddToCart])
def checkout(self, request):
    """
    Checkout - Create order from cart.
    @transaction.atomic ensures all DB writes succeed or all rollback.
    """
    serializer = CheckoutSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    cart = Cart.objects.get(user=request.user)
    order = Order.objects.create(user=request.user, status='pending')

    for cart_item in cart.items.filter(is_active=True):
        OrderItem.objects.create(order=order, **cart_item_data)

    cart.items.filter(is_active=True).update(is_active=False)  # Clear cart
    return Response({'message': 'Order created'}, status=status.HTTP_201_CREATED)
```
> **Key:** `@transaction.atomic` + `@action` can be **stacked** together.

---

#### Example 4 — `accounts/UserViewSet.py`: Team hierarchy endpoint
```python
@swagger_auto_schema(
    tags=["02. User Management"],
    operation_description="Get all subordinates (direct + indirect) of the current user",
)
@action(detail=False, methods=['get'], url_path='my-team',
        permission_classes=[IsAuthenticated, CanViewHierarchy])
def my_team(self, request):
    """Get all subordinates of the current user"""
    sales_profile = getattr(request.user, 'sales_profile', None)
    if not sales_profile:
        return Response(
            {'error': 'Only sales staff can view their team'},
            status=status.HTTP_403_FORBIDDEN
        )

    subordinates = sales_profile.get_all_subordinates(include_self=False)
    subordinate_users = User.objects.filter(
        sales_profile__in=subordinates
    ).select_related('sales_profile')

    serializer = UserSerializer(subordinate_users, many=True)
    return Response({'count': subordinate_users.count(), 'subordinates': serializer.data})
```
> **URL generated:** `GET /api/users/my-team/`

---

#### Example 5 — `accounts/UserViewSet.py`: Reporting chain
```python
@action(detail=False, methods=['get'], url_path='my-reporting-chain',
        permission_classes=[IsAuthenticated, CanViewHierarchy])
def my_reporting_chain(self, request):
    """Get upward reporting chain: self → manager → CEO"""
    chain = request.user.sales_profile.get_reporting_chain(include_self=True)
    chain_data = [
        {
            'id': profile.id,
            'name': str(profile),
            'designation': profile.designation,
            'level': level,
            'is_self': (level == 0)
        }
        for level, profile in enumerate(chain)
    ]
    return Response({'chain': chain_data})
```
> **URL generated:** `GET /api/users/my-reporting-chain/`

---

### `detail=True` vs `detail=False` — Summary

```
detail=False  →  /api/cart/add-item/          (no ID in URL)
detail=True   →  /api/users/{id}/permissions/ (ID required)
```

---

## 2. `@api_view` Decorator

### What is it?
`@api_view` converts a **regular Python function** into a DRF API view. Without it, DRF features like authentication, permissions, and `Response` don't work.

### Import
```python
from rest_framework.decorators import api_view
```

### Real Examples from This Project

#### Example 1 — `sap_integration/views.py`: Simple GET endpoint
```python
from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['GET'])
def get_sap_policies(request):
    """Fetch policies from SAP"""
    database = request.GET.get('database')
    if not database:
        return Response({'error': 'database parameter required'}, status=400)
    # ... fetch from SAP
    return Response({'policies': data})
```

#### Example 2 — `kindwise/views.py`: Multiple methods on same function
```python
@swagger_auto_schema(method='post', ...)  # Swagger for POST
@swagger_auto_schema(method='get', ...)   # Swagger for GET
@api_view(['GET', 'POST'])
@parser_classes([MultiPartParser])
def identify_view(request):
    """Handle both GET (list) and POST (upload image)"""
    if request.method == 'POST':
        image_file = request.FILES.get('image')
        image_data = image_file.read()
        result = identify_crop(base64.b64encode(image_data).decode('utf-8'))
        return JsonResponse({'result': result})

    # GET: list records
    user_id = request.GET.get('user_id')
    qs = KindwiseIdentification.objects.filter(user_id=user_id)
    return JsonResponse({'count': qs.count(), 'results': list(qs)}, safe=False)
```

#### Example 3 — `accounts/views.py`: With permission decorator
```python
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_territories_emp_api(request, user_id):
    """Get user's sales territories"""
    profile = (
        SalesStaffProfile.objects
        .select_related('user')
        .prefetch_related(
            'companies',
            'regions__company',
            'zones__region__company',
            'territories__zone__region__company'
        )
        .get(user_id=user_id)
    )
    return Response({'companies': [...], 'sap_emp_id': profile.employee_code})
```

---

### `@api_view` vs Class-Based Views

| Feature | `@api_view` | `ViewSet` / `APIView` |
|---------|------------|----------------------|
| Style | Function-based | Class-based |
| Routing | Manual `urlpatterns` | Router auto-generates URLs |
| Best for | Simple, one-off endpoints | CRUD operations |
| Used in project | `sap_integration/views.py`, `kindwise/views.py` | `cart/views.py`, `accounts/UserViewSet.py` |

---

## 3. `@permission_classes` Decorator

### What is it?
Overrides the **default permission classes** for a specific function-based view.

### Import
```python
from rest_framework.decorators import permission_classes
```

### Real Example from This Project

```python
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from accounts.permissions import HasRolePermission

@api_view(['GET'])
@permission_classes([IsAuthenticated, HasRolePermission])
def get_roles(request):
    """Only authenticated users with a role can access"""
    roles = Role.objects.all()
    return Response(RoleSerializer(roles, many=True).data)
```

### Overriding Permissions Per Action in ViewSets

```python
# accounts/UserViewSet.py
class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]  # Default

    def get_permissions(self):
        """Override permissions per action"""
        if self.action == 'destroy':
            return [permissions.IsAdminUser()]  # Only admin can delete
        return [IsAuthenticated(), IsOwnerOrAdmin()]  # Others: owner or admin

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated, CanViewHierarchy])  # Per-action override
    def my_team(self, request):
        ...
```

---

## 4. `@parser_classes` Decorator

### What is it?
Specifies which **content types** the view can parse (JSON, multipart/form-data, etc.).

### Import
```python
from rest_framework.decorators import parser_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
```

### Real Example — `kindwise/views.py`: File Upload
```python
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser

@api_view(['GET', 'POST'])
@parser_classes([MultiPartParser])  # Only accept multipart (file uploads)
def identify_view(request):
    """
    POST: Upload image file for crop identification
    MultiPartParser allows request.FILES to work
    """
    if request.method == 'POST':
        image_file = request.FILES.get('image')  # Access uploaded file
        image_data = image_file.read()
        image_b64 = base64.b64encode(image_data).decode('utf-8')
        result = identify_crop(image_b64)
        return JsonResponse({'result': result})
```

### Parser Types

| Parser | Content-Type | Use Case |
|--------|-------------|----------|
| `JSONParser` | `application/json` | Standard API requests |
| `MultiPartParser` | `multipart/form-data` | File uploads |
| `FormParser` | `application/x-www-form-urlencoded` | HTML form submissions |
| `FileUploadParser` | Any binary | Raw file uploads |

### In Class-Based Views (UserViewSet.py)
```python
from rest_framework.parsers import MultiPartParser, FormParser

class UserViewSet(viewsets.ModelViewSet):
    parser_classes = [MultiPartParser, FormParser]  # Accept files + form data
    # This allows profile_image uploads in user create/update
```

---

## 5. `Response`

### What is it?
DRF's `Response` class automatically **serializes data to JSON** (or other formats) and sets the correct `Content-Type` header.

### Import
```python
from rest_framework.response import Response
```

### Why use DRF `Response` instead of Django's `JsonResponse`?

| Feature | `Response` (DRF) | `JsonResponse` (Django) |
|---------|-----------------|------------------------|
| Content negotiation | ✅ Auto (JSON, XML, etc.) | ❌ JSON only |
| Works with DRF renderers | ✅ Yes | ❌ No |
| Status codes | ✅ `status=status.HTTP_200_OK` | ✅ `status=200` |
| Used in project | ViewSets, api_view | `kindwise/views.py` (legacy) |

### Real Examples from This Project

```python
# Success response
return Response({'message': 'Item added to cart', 'item': item_data}, status=status.HTTP_201_CREATED)

# Error response
return Response({'error': 'user_id parameter is required.'}, status=status.HTTP_400_BAD_REQUEST)

# Forbidden
return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

# Serializer data
serializer = CartSerializer(cart)
return Response(serializer.data)  # Automatically converts to JSON

# Paginated response
page = paginator.paginate_queryset(queryset, request)
serializer = CartItemSerializer(page, many=True)
return paginator.get_paginated_response(serializer.data)
```

### Common Status Codes Used in This Project

```python
from rest_framework import status

status.HTTP_200_OK           # 200 - Success
status.HTTP_201_CREATED      # 201 - Created (POST success)
status.HTTP_204_NO_CONTENT   # 204 - Deleted (no body returned)
status.HTTP_400_BAD_REQUEST  # 400 - Validation error / missing params
status.HTTP_401_UNAUTHORIZED # 401 - Not logged in
status.HTTP_403_FORBIDDEN    # 403 - Logged in but no permission
status.HTTP_404_NOT_FOUND    # 404 - Object not found
status.HTTP_503_SERVICE_UNAVAILABLE  # 503 - External service down (SAP/HANA)
```

---

## 6. `viewsets` & `status`

### Import
```python
from rest_framework import viewsets, status
```

### ViewSet Types

| ViewSet | What it provides | Used in project |
|---------|-----------------|----------------|
| `viewsets.ViewSet` | Only `list()`, custom actions | `CartViewSet` |
| `viewsets.ModelViewSet` | Full CRUD (list, create, retrieve, update, destroy) | `OrderViewSet`, `UserViewSet` |
| `viewsets.ReadOnlyModelViewSet` | Only `list()` and `retrieve()` | — |
| `viewsets.GenericViewSet` | Mixins only, no default actions | — |

### Real Example — `cart/views.py`
```python
from rest_framework import viewsets, status

class CartViewSet(viewsets.ViewSet):
    """
    Custom ViewSet - only has actions we define with @action
    No automatic CRUD (no create/update/destroy)
    """
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """GET /api/cart/ — manually defined"""
        cart = Cart.objects.get(user=request.user)
        return Response(CartSerializer(cart).data)

    @action(detail=False, methods=['post'])
    def add_item(self, request):
        """POST /api/cart/add-item/"""
        return Response({'status': 'added'}, status=status.HTTP_201_CREATED)


class OrderViewSet(viewsets.ModelViewSet):
    """
    Full CRUD ViewSet
    Automatically provides: list, create, retrieve, update, partial_update, destroy
    """
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated, CanViewOrderHistory]

    def get_queryset(self):
        """Customize queryset based on user"""
        # Short-circuit during Swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return Order.objects.none()

        user = self.request.user
        if user.is_superuser or user.has_perm('cart.manage_orders'):
            return Order.objects.all().prefetch_related('items')
        return Order.objects.filter(user=user).prefetch_related('items')

    def get_serializer_class(self):
        """Return different serializer for list vs detail"""
        if self.action == 'list':
            return OrderListSerializer  # Lightweight
        return OrderSerializer  # Full details
```

### `swagger_fake_view` — Important Pattern
```python
def get_queryset(self):
    # This prevents errors when Swagger generates schema
    if getattr(self, 'swagger_fake_view', False):
        return Order.objects.none()
    # Normal logic below
    return Order.objects.filter(user=self.request.user)
```
> **Why?** When `drf-yasg` generates the Swagger schema, it calls `get_queryset()` without a real request. `swagger_fake_view=True` is set by yasg, so we return an empty queryset to avoid `AttributeError: 'NoneType' object has no attribute 'user'`.

---

## 7. `IsAuthenticated` & Other Permissions

### Import
```python
from rest_framework.permissions import IsAuthenticated
```

### All Permission Classes Used in This Project

```python
from rest_framework.permissions import (
    IsAuthenticated,         # Must be logged in
    IsAdminUser,             # Must be is_staff=True
    AllowAny,                # No auth required
)
from accounts.permissions import HasRolePermission    # Custom: check role-based perms
from accounts.hierarchy_permissions import (
    CanViewHierarchy,        # Custom: can view team hierarchy
    CanManageHierarchy,      # Custom: can manage team hierarchy
)
from cart.permissions import (
    CanAddToCart,            # Custom: has 'cart.add_cartitem' permission
    CanManageCart,           # Custom: can manage cart
    CanViewOrderHistory,     # Custom: has 'cart.view_order' permission
    CanManageOrders,         # Custom: has 'cart.manage_orders' permission
    IsOrderOwner,            # Custom: owns the order
)
```

### How Custom Permissions Work

```python
# accounts/permissions.py
from rest_framework.permissions import BasePermission

class HasRolePermission(BasePermission):
    """
    Checks if the user's role has the required Django permission.
    Superusers always pass.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        # Check Django model permission
        required_perm = getattr(view, 'required_permission', None)
        if required_perm:
            return request.user.has_perm(required_perm)
        return True
```

### Combining Multiple Permissions (ALL must pass)
```python
class CartViewSet(viewsets.ViewSet):
    # Default: must be authenticated
    permission_classes = [IsAuthenticated]

    # This action: must be authenticated AND have CanAddToCart
    @action(detail=False, methods=['post'],
            permission_classes=[IsAuthenticated, CanAddToCart])
    def add_item(self, request):
        ...
```

---

## 8. Parsers

### Import
```python
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
```

### Real Usage — `accounts/UserViewSet.py`
```python
class UserViewSet(viewsets.ModelViewSet):
    # Accept both file uploads and form data
    parser_classes = [MultiPartParser, FormParser]

    # This allows:
    # - profile_image file upload (MultiPartParser)
    # - form fields like username, email (FormParser)
```

### When to Use Which Parser

```python
# JSON API (default, no need to specify)
parser_classes = [JSONParser]
# Request: Content-Type: application/json
# Body: {"username": "john", "email": "john@example.com"}

# File upload
parser_classes = [MultiPartParser, FormParser]
# Request: Content-Type: multipart/form-data
# Body: form fields + file

# Both JSON and files
parser_classes = [MultiPartParser, FormParser, JSONParser]
```

---

## 9. `SearchFilter` & `OrderingFilter`

### Import
```python
from rest_framework.filters import SearchFilter, OrderingFilter
```

### Real Usage — `accounts/UserViewSet.py`
```python
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter

class UserViewSet(viewsets.ModelViewSet):
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]

    # SearchFilter: ?search=john
    search_fields = [
        'username', 'email', 'first_name', 'last_name',
        'sales_profile__employee_code',   # Search across related model
        'sales_profile__designation'
    ]

    # OrderingFilter: ?ordering=email or ?ordering=-date_joined
    ordering_fields = [
        'id', 'username', 'email', 'first_name', 'last_name',
        'is_active', 'role',
        'sales_profile__employee_code',
        'sales_profile__designation'
    ]
    ordering = ['id']  # Default ordering
```

### How to Use in API Calls
```
GET /api/users/?search=john              → Search by name/email
GET /api/users/?ordering=email           → Sort A-Z by email
GET /api/users/?ordering=-date_joined    → Sort newest first
GET /api/users/?is_active=true&role=5   → Filter (DjangoFilterBackend)
```

---

## 10. `PageNumberPagination`

### Import
```python
from rest_framework.pagination import PageNumberPagination
```

### Real Usage — `cart/views.py` (Dynamic Pagination)
```python
from rest_framework.pagination import PageNumberPagination

@action(detail=False, methods=['get'])
def items(self, request):
    """List cart items with pagination"""
    queryset = cart.items.all()

    # Dynamic pagination
    paginator = PageNumberPagination()

    # Custom page size from query param
    page_size = request.query_params.get('page_size')
    if page_size:
        try:
            page_size = int(page_size)
            if page_size > 100:
                page_size = 100  # Cap at 100
            paginator.page_size = page_size
        except ValueError:
            pass

    page = paginator.paginate_queryset(queryset, request)
    if page is not None:
        serializer = CartItemSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
        # Returns: {"count": 50, "next": "...", "previous": "...", "results": [...]}

    serializer = CartItemSerializer(queryset, many=True)
    return Response(serializer.data)
```

### Paginated Response Structure
```json
{
    "count": 50,
    "next": "http://localhost:8000/api/cart/items/?page=2",
    "previous": null,
    "results": [
        {"id": 1, "product_name": "Fertilizer", "quantity": 2}
    ]
}
```

---

## 11. `@swagger_auto_schema`

### What is it?
Customizes how an endpoint appears in the **Swagger UI** (`/swagger/`). Without it, DRF-yasg auto-generates basic docs.

### Import
```python
from drf_yasg.utils import swagger_auto_schema, no_body
```

### Real Example — `cart/views.py`
```python
@swagger_auto_schema(
    operation_id='get_user_cart',
    operation_description="Get user's cart with summary. Requires user_id parameter.",
    manual_parameters=[
        openapi.Parameter(
            'user_id',
            openapi.IN_QUERY,
            description="User ID (required). Users can only access their own cart.",
            type=openapi.TYPE_INTEGER,
            required=True
        ),
        openapi.Parameter(
            'include_expired',
            openapi.IN_QUERY,
            description="Include expired items (default: false)",
            type=openapi.TYPE_BOOLEAN,
            required=False
        ),
    ],
    responses={
        200: CartSerializer(),
        400: "Bad request - missing or invalid user_id",
        401: "Unauthorized - authentication required",
        403: "Forbidden - cannot access another user's cart",
        404: "Not found - user does not exist"
    },
    tags=["06. Shopping Cart"]
)
def list(self, request):
    ...
```

### Real Example — `kindwise/views.py`: `no_body` for file upload
```python
from drf_yasg.utils import swagger_auto_schema, no_body

@swagger_auto_schema(
    method='post',
    operation_description="Identify crop from image (Multipart File Upload).",
    consumes=['multipart/form-data'],
    manual_parameters=[
        openapi.Parameter(
            name="image",
            in_=openapi.IN_FORM,
            type=openapi.TYPE_FILE,
            description="Image file upload",
            required=True
        )
    ],
    request_body=no_body,  # ← Prevents conflict with manual_parameters
)
@api_view(['POST'])
@parser_classes([MultiPartParser])
def identify_view(request):
    ...
```
> **`no_body`** is used when you have `manual_parameters` with `IN_FORM` — you can't have both a `request_body` and form parameters at the same time.

### Applying to Multiple Methods on Same Function
```python
@swagger_auto_schema(method='post', ...)  # Docs for POST
@swagger_auto_schema(method='get', ...)   # Docs for GET
@api_view(['GET', 'POST'])
def my_view(request):
    ...
```

### `swagger_auto_schema` Parameters Reference

| Parameter | Purpose | Example |
|-----------|---------|---------|
| `operation_description` | Description shown in Swagger | `"Get user cart"` |
| `operation_id` | Unique ID for the operation | `'get_user_cart'` |
| `manual_parameters` | Query/path/form params | `[openapi.Parameter(...)]` |
| `request_body` | Body schema | `CartSerializer()` or `no_body` |
| `responses` | Document response codes | `{200: CartSerializer(), 404: "Not found"}` |
| `tags` | Group endpoints in Swagger UI | `["06. Shopping Cart"]` |
| `consumes` | Content types accepted | `['multipart/form-data']` |

---

## 12. `openapi`

### Import
```python
from drf_yasg import openapi
```

### Parameter Locations (`IN_*`)

```python
openapi.IN_QUERY   # ?param=value in URL
openapi.IN_PATH    # /api/users/{id}/ — path variable
openapi.IN_FORM    # Form field (multipart/form-data)
openapi.IN_HEADER  # HTTP header
openapi.IN_BODY    # Request body (deprecated, use request_body)
```

### Data Types

```python
openapi.TYPE_STRING   # "hello"
openapi.TYPE_INTEGER  # 42
openapi.TYPE_BOOLEAN  # true/false
openapi.TYPE_NUMBER   # 3.14
openapi.TYPE_ARRAY    # [1, 2, 3]
openapi.TYPE_OBJECT   # {"key": "value"}
openapi.TYPE_FILE     # File upload
```

### Real Examples from This Project

```python
# Simple string param
openapi.Parameter('database', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False)

# Integer param (required)
openapi.Parameter('user_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True)

# Boolean param
openapi.Parameter('is_active', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN)

# Array param (from accounts/UserViewSet.py)
openapi.Parameter(
    'companies',
    openapi.IN_QUERY,
    type=openapi.TYPE_ARRAY,
    items=openapi.Items(type=openapi.TYPE_INTEGER),
    description="Filter by company IDs"
)

# File upload (from kindwise/views.py)
openapi.Parameter(
    name="image",
    in_=openapi.IN_FORM,
    type=openapi.TYPE_FILE,
    description="Image file upload",
    required=True
)

# Custom response schema (from cart/views.py)
openapi.Response(
    'Paginated cart items',
    schema=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'count': openapi.Schema(type=openapi.TYPE_INTEGER),
            'next': openapi.Schema(type=openapi.TYPE_STRING, format='uri', nullable=True),
            'results': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT)),
        }
    )
)

# Request body schema (from cart/views.py)
request_body=openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=['user_id', 'cart_id'],
    properties={
        'user_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='User ID'),
        'cart_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Cart ID'),
    }
)
```

---

## 13. `@transaction.atomic`

### Import
```python
from django.db import transaction
```

### What is it?
Wraps database operations in a **transaction** — if any operation fails, **all changes are rolled back**.

### Real Examples from This Project

#### As a decorator on ViewSet method — `accounts/UserViewSet.py`
```python
@swagger_auto_schema(tags=["02. User Management"], ...)
@transaction.atomic
def create(self, request, *args, **kwargs):
    """
    Create user + SalesStaffProfile + Dealer in one atomic transaction.
    If dealer creation fails, user is also rolled back.
    """
    serializer = self.get_serializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    # Create user
    user = User(**serializer.validated_data)
    user.save()

    # Create sales profile
    if is_sales_staff:
        profile = SalesStaffProfile.objects.create(user=user)
        profile.companies.set(company_ids)

    # Create dealer profile
    if is_dealer and dealer_data:
        dealer = Dealer.objects.create(user=user, **dealer_data)

    return Response(self.get_serializer(user).data, status=status.HTTP_201_CREATED)
```

#### Stacked with `@action` — `cart/views.py`
```python
@transaction.atomic
@action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, CanAddToCart])
def checkout(self, request):
    """
    Create order + order items + clear cart — all or nothing.
    If any step fails, everything rolls back.
    """
    order = Order.objects.create(user=request.user, status='pending')

    for cart_item in cart_items:
        OrderItem.objects.create(order=order, ...)

    order.total_amount = total
    order.save()

    cart_items.update(is_active=False)  # Clear cart

    return Response({'order': OrderSerializer(order).data}, status=status.HTTP_201_CREATED)
```

### Decorator Order Matters!
```python
# CORRECT — transaction wraps the action
@transaction.atomic
@action(detail=False, methods=['post'])
def checkout(self, request):
    ...

# ALSO CORRECT — as context manager
@action(detail=False, methods=['post'])
def checkout(self, request):
    with transaction.atomic():
        order = Order.objects.create(...)
        OrderItem.objects.create(order=order, ...)
```

---

## 14. `DjangoFilterBackend`

### Import
```python
from django_filters.rest_framework import DjangoFilterBackend
```

### Real Usage — `accounts/UserViewSet.py`
```python
from django_filters.rest_framework import DjangoFilterBackend
from .filters import UserFilter

class UserViewSet(viewsets.ModelViewSet):
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_class = UserFilter  # Custom FilterSet class

# accounts/filters.py
import django_filters
from .models import User

class UserFilter(django_filters.FilterSet):
    is_active = django_filters.BooleanFilter()
    role = django_filters.NumberFilter()
    is_sales_staff = django_filters.BooleanFilter()

    class Meta:
        model = User
        fields = ['is_active', 'role', 'is_sales_staff']
```

### Usage in API
```
GET /api/users/?is_active=true          → Filter active users
GET /api/users/?role=5                  → Filter by role ID
GET /api/users/?is_sales_staff=true     → Filter sales staff only
```

---

## 15. `APIView`

### Import
```python
from rest_framework.views import APIView
```

### What is it?
A class-based view that gives you full control over each HTTP method.

### Real Usage — `cart/views.py`
```python
from rest_framework.views import APIView

class CartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Handle GET /api/cart/"""
        cart = Cart.objects.get(user=request.user)
        return Response(CartSerializer(cart).data)

    def post(self, request):
        """Handle POST /api/cart/"""
        # Add item logic
        return Response({'status': 'added'}, status=status.HTTP_201_CREATED)

    def delete(self, request):
        """Handle DELETE /api/cart/"""
        Cart.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
```

### `APIView` vs `ViewSet` vs `@api_view`

| | `@api_view` | `APIView` | `ViewSet` |
|--|------------|-----------|-----------|
| Style | Function | Class | Class |
| URL routing | Manual | Manual | Router auto-generates |
| HTTP methods | Listed in decorator | Defined as methods | Actions (list, create, etc.) |
| Best for | Simple endpoints | Custom logic per method | CRUD + custom actions |
| Project examples | `sap_integration/views.py` | `cart/views.py` | `accounts/UserViewSet.py` |

---

## Quick Reference: All Imports Used in This Project

```python
# ── DRF Core ──────────────────────────────────────────────
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action, api_view, permission_classes, parser_classes

# ── Permissions ───────────────────────────────────────────
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from accounts.permissions import HasRolePermission
from accounts.hierarchy_permissions import CanViewHierarchy, CanManageHierarchy
from cart.permissions import CanAddToCart, CanViewOrderHistory, IsOrderOwner

# ── Parsers ───────────────────────────────────────────────
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

# ── Filters ───────────────────────────────────────────────
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

# ── Pagination ────────────────────────────────────────────
from rest_framework.pagination import PageNumberPagination

# ── Swagger / OpenAPI ─────────────────────────────────────
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi

# ── Django DB ─────────────────────────────────────────────
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Sum, Prefetch

# ── Django Auth ───────────────────────────────────────────
from django.contrib.auth import get_user_model

# ── Logging ───────────────────────────────────────────────
import logging
logger = logging.getLogger(__name__)
```

---

## Common Patterns & Interview Tips

### Pattern 1: Stacking Decorators
```python
# Order matters: decorators apply bottom-up
@swagger_auto_schema(...)   # 3rd applied
@transaction.atomic          # 2nd applied
@action(detail=False, ...)   # 1st applied (closest to function)
def checkout(self, request):
    ...
```

### Pattern 2: `get_serializer_class()` — Dynamic Serializer
```python
# cart/views.py
class OrderViewSet(viewsets.ModelViewSet):
    def get_serializer_class(self):
        if self.action == 'list':
            return OrderListSerializer   # Lightweight for lists
        return OrderSerializer           # Full details for single object
```

### Pattern 3: `get_permissions()` — Dynamic Permissions
```python
# accounts/UserViewSet.py
class UserViewSet(viewsets.ModelViewSet):
    def get_permissions(self):
        if self.action == 'destroy':
            return [permissions.IsAdminUser()]
        return [IsAuthenticated(), IsOwnerOrAdmin()]
```

### Pattern 4: `swagger_fake_view` Guard
```python
def get_queryset(self):
    # Prevent Swagger schema generation errors
    if getattr(self, 'swagger_fake_view', False):
        return Order.objects.none()
    return Order.objects.filter(user=self.request.user)
```

### Pattern 5: `raise_exception=True` in Serializer Validation
```python
serializer = AddToCartSerializer(data=request.data)
serializer.is_valid(raise_exception=True)  # Automatically returns 400 if invalid
# No need for: if not serializer.is_valid(): return Response(serializer.errors, status=400)
```

---

*This guide covers all DRF decorators and important imports used across the Django Web Portal project.*

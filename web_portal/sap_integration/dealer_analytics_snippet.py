@swagger_auto_schema(
    tags=['SAP - Dealer Analytics'], 
    method='get',
    operation_summary="Dealer Analytics Dashboard",
    operation_description="""
    Get comprehensive analytics for a dealer user.
    
    **This endpoint provides:**
    - Dealer's card_code from user_id
    - Total complaints/requests submitted last month
    - Total active policies for this dealer
    - Total Kindwise plant identification records
    
    **Usage:**
    - Provide user_id to get dealer analytics
    - Returns 404 if dealer not found for user_id
    - Returns 404 if no card_code assigned to dealer
    
    **Example Request:**
    ```
    GET /api/sap/dealer-analytics/?user_id=123&database=4B-AGRI_LIVE
    ```
    
    **Example Response:**
    ```json
    {
        "success": true,
        "user_id": 123,
        "card_code": "C00123",
        "dealer_name": "John Doe",
        "business_name": "ABC Traders",
        "analytics": {
            "complaints_last_month": 5,
            "total_policies": 3,
            "total_kindwise_records": 12,
            "last_month_start": "2026-01-01",
            "last_month_end": "2026-01-31"
        }
    }
    ```
    """,
    manual_parameters=[
        openapi.Parameter(
            'user_id', 
            openapi.IN_QUERY, 
            description="Portal User ID (required). Example: 123", 
            type=openapi.TYPE_INTEGER, 
            required=True
        ),
        openapi.Parameter(
            'database', 
            openapi.IN_QUERY, 
            description="SAP HANA database/schema name (e.g., 4B-AGRI_LIVE, 4B-BIO_APP). If not provided, uses default.", 
            type=openapi.TYPE_STRING, 
            required=False
        ),
    ],
    responses={
        200: openapi.Response(
            description="Dealer analytics retrieved successfully",
            examples={
                "application/json": {
                    "success": True,
                    "user_id": 123,
                    "card_code": "C00123",
                    "dealer_name": "John Doe",
                    "business_name": "ABC Traders",
                    "analytics": {
                        "complaints_last_month": 5,
                        "total_policies": 3,
                        "total_kindwise_records": 12,
                        "last_month_start": "2026-01-01",
                        "last_month_end": "2026-01-31"
                    }
                }
            }
        ),
        400: openapi.Response(
            description="Bad request - missing user_id",
            examples={
                "application/json": {
                    "success": False,
                    "error": "user_id parameter is required"
                }
            }
        ),
        404: openapi.Response(
            description="Dealer not found",
            examples={
                "application/json": {
                    "success": False,
                    "error": "Dealer not found for user_id: 123"
                }
            }
        ),
        500: openapi.Response(
            description="Server error",
            examples={
                "application/json": {
                    "success": False,
                    "error": "Database connection failed"
                }
            }
        )
    }
)
@api_view(['GET'])
def dealer_analytics_api(request):
    """
    Get dealer analytics dashboard data
    
    Query Parameters:
        - user_id (required): Portal user ID
        - database (optional): SAP HANA schema name
    
    Returns:
        JSON response with dealer analytics
    """
    try:
        # Get user_id parameter
        user_id = request.GET.get('user_id', '').strip()
        
        # Validate user_id parameter
        if not user_id:
            return Response({
                'success': False,
                'error': 'user_id parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user_id = int(user_id)
        except ValueError:
            return Response({
                'success': False,
                'error': 'user_id must be a valid integer'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get dealer by user_id
        from FieldAdvisoryService.models import Dealer, DealerRequest
        from kindwise.models import KindwiseIdentification
        from datetime import datetime, timedelta
        from dateutil.relativedelta import relativedelta
        
        try:
            dealer = Dealer.objects.select_related('user').get(user_id=user_id)
        except Dealer.DoesNotExist:
            return Response({
                'success': False,
                'error': f'Dealer not found for user_id: {user_id}'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if dealer has card_code
        if not dealer.card_code:
            return Response({
                'success': False,
                'error': f'Dealer (user_id: {user_id}) does not have a card_code assigned'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Calculate last month date range
        today = datetime.now()
        last_month_end = today.replace(day=1) - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        
        # Count complaints/dealer requests submitted last month
        complaints_count = DealerRequest.objects.filter(
            dealer=dealer,
            created_at__gte=last_month_start,
            created_at__lte=last_month_end.replace(hour=23, minute=59, second=59)
        ).count()
        
        # Get total Kindwise records for this user
        kindwise_count = KindwiseIdentification.objects.filter(user_id=user_id).count()
        
        # Get total policies from SAP HANA
        database = get_hana_schema_from_request(request)
        
        total_policies = 0
        policies_error = None
        
        try:
            # Load environment variables
            try:
                _hana_load_env_file(os.path.join(os.path.dirname(__file__), '.env'))
                _hana_load_env_file(os.path.join(str(settings.BASE_DIR), '.env'))
                _hana_load_env_file(os.path.join(str(Path(settings.BASE_DIR).parent), '.env'))
                _hana_load_env_file(os.path.join(os.getcwd(), '.env'))
            except Exception:
                pass
            
            # Get SAP HANA connection configuration
            cfg = {
                'host': os.environ.get('HANA_HOST', ''),
                'port': os.environ.get('HANA_PORT', '30015'),
                'user': os.environ.get('HANA_USER', ''),
                'encrypt': os.environ.get('HANA_ENCRYPT', ''),
                'ssl_validate': os.environ.get('HANA_SSL_VALIDATE', ''),
                'schema': database
            }
            
            pwd = os.environ.get('HANA_PASSWORD', '')
            
            if all([cfg['host'], cfg['port'], cfg['user'], pwd]):
                from hdbcli import dbapi
                
                kwargs = {
                    'address': cfg['host'],
                    'port': int(cfg['port']),
                    'user': cfg['user'],
                    'password': pwd
                }
                
                if str(cfg['encrypt']).strip().lower() in ('true', '1', 'yes'):
                    kwargs['encrypt'] = True
                    if cfg['ssl_validate']:
                        kwargs['sslValidateCertificate'] = (str(cfg['ssl_validate']).strip().lower() in ('true', '1', 'yes'))
                
                try:
                    conn = dbapi.connect(**kwargs)
                    try:
                        # Set schema
                        cur = conn.cursor()
                        if cfg['schema']:
                            from sap_integration.hana_connect import quote_ident
                            schema_name = cfg['schema']
                            set_schema_sql = f'SET SCHEMA {quote_ident(schema_name)}'
                            cur.execute(set_schema_sql)
                        
                        # Get policy count using policy_customer_balance
                        from .hana_connect import policy_customer_balance
                        policies_data = policy_customer_balance(conn, dealer.card_code)
                        
                        if policies_data:
                            total_policies = len(policies_data)
                        
                        cur.close()
                    finally:
                        conn.close()
                        
                except Exception as e:
                    policies_error = str(e)
            else:
                policies_error = "SAP HANA configuration is incomplete"
                
        except Exception as e:
            policies_error = str(e)
        
        # Build response
        response_data = {
            'success': True,
            'user_id': user_id,
            'card_code': dealer.card_code,
            'dealer_name': dealer.name,
            'business_name': dealer.business_name or '',
            'analytics': {
                'complaints_last_month': complaints_count,
                'total_policies': total_policies,
                'total_kindwise_records': kindwise_count,
                'last_month_start': last_month_start.strftime('%Y-%m-%d'),
                'last_month_end': last_month_end.strftime('%Y-%m-%d')
            }
        }
        
        # Add error info if policies fetch failed
        if policies_error:
            response_data['analytics']['policies_error'] = policies_error
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': f'An error occurred: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

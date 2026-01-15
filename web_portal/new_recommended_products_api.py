"""
View function to query diseases and products directly from SAP HANA
Replace the recommended_products_api function in views.py with this
"""

@api_view(['GET'])
def recommended_products_api(request):
    """Get recommended products for a disease - queries directly from SAP @ODID and OITM tables"""
    try:
        from hdbcli import dbapi
        
        disease_id = request.GET.get('disease_id')
        item_code = request.GET.get('item_code', '').strip()
        disease_name = request.GET.get('disease_name', '').strip()
        
        # Get database parameter
        hana_schema = get_hana_schema_from_request(request)
        if not hana_schema:
            return Response({
                'success': False,
                'error': 'Database parameter is required (e.g., database=4B-BIO_APP or database=4B-ORANG_APP)'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Load environment variables
        _hana_load_env_file(os.path.join(os.path.dirname(__file__), '.env'))
        _hana_load_env_file(os.path.join(str(settings.BASE_DIR), '.env'))
        _hana_load_env_file(os.path.join(str(Path(settings.BASE_DIR).parent), '.env'))
        _hana_load_env_file(os.path.join(os.getcwd(), '.env'))
        
        cfg = {
            'host': os.environ.get('HANA_HOST') or '',
            'port': os.environ.get('HANA_PORT') or '',
            'user': os.environ.get('HANA_USER') or '',
            'encrypt': os.environ.get('HANA_ENCRYPT') or '',
            'schema': hana_schema
        }
        
        pwd = os.environ.get('HANA_PASSWORD', '')
        kwargs = {
            'address': cfg['host'],
            'port': int(cfg['port']),
            'user': cfg['user'],
            'password': pwd
        }
        
        if str(cfg['encrypt']).strip().lower() in ('true', '1', 'yes'):
            kwargs['encrypt'] = True
            kwargs['sslValidateCertificate'] = False
        
        conn = dbapi.connect(**kwargs)
        
        try:
            # Set schema
            cur = conn.cursor()
            cur.execute(f'SET SCHEMA "{cfg["schema"]}"')
            cur.close()
            
            # Query @ODID table for disease
            disease_info = None
            product_item_codes = []
            
            if item_code:
                # Query by specific item code
                cur = conn.cursor()
                cur.execute(
                    'SELECT "DocEntry", "U_ItemCode", "U_ItemName", "U_Description", "U_Disease" '
                    'FROM "@ODID" WHERE "U_ItemCode" = ?',
                    (item_code,)
                )
                row = cur.fetchone()
                if row:
                    disease_info = {
                        'doc_entry': row[0],
                        'item_code': row[1],
                        'item_name': row[2],
                        'description': row[3],
                        'disease_name': row[4]
                    }
                    product_item_codes = [row[1]]
                cur.close()
            elif disease_name:
                # Query by disease name - can return multiple item codes for same disease
                cur = conn.cursor()
                cur.execute(
                    'SELECT "DocEntry", "U_ItemCode", "U_ItemName", "U_Description", "U_Disease" '
                    'FROM "@ODID" WHERE UPPER("U_Disease") = ? OR UPPER("U_ItemCode") = ? OR UPPER("U_ItemName") = ?',
                    (disease_name.upper(), disease_name.upper(), disease_name.upper())
                )
                rows = cur.fetchall()
                if rows:
                    # Use first row for disease info
                    disease_info = {
                        'doc_entry': rows[0][0],
                        'item_code': rows[0][1],
                        'item_name': rows[0][2],
                        'description': rows[0][3],
                        'disease_name': rows[0][4]
                    }
                    # Collect ALL item codes for this disease
                    product_item_codes = [row[1] for row in rows if row[1]]
                cur.close()
            else:
                conn.close()
                return Response({
                    'success': False,
                    'error': 'Either item_code or disease_name parameter is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not disease_info:
                conn.close()
                return Response({
                    'success': False,
                    'error': f'Disease not found in SAP @ODID table'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Fetch product details from OITM for all item codes
            products_data = []
            
            if product_item_codes:
                # Extract database folder name for images
                db_name = hana_schema.upper()
                if '4B-BIO' in db_name:
                    folder_name = '4B-BIO'
                elif '4B-ORANG' in db_name:
                    folder_name = '4B-ORANG'
                else:
                    folder_name = 'default'
                
                for idx, prod_code in enumerate(product_item_codes, 1):
                    try:
                        cur = conn.cursor()
                        sql = '''
                        SELECT 
                            T0."ItemCode",
                            T0."ItemName",
                            T1."ItmsGrpNam",
                            T0."SalPackMsr",
                            T0."InvntryUom",
                            T0."U_GenericName",
                            T0."U_BrandName",
                            PI."FileName" AS "Image_File",
                            PI."FileExt" AS "Image_Ext",
                            PU."FileName" AS "Urdu_File",
                            PU."FileExt" AS "Urdu_Ext"
                        FROM OITM T0
                        INNER JOIN OITB T1 ON T0."ItmsGrpCod" = T1."ItmsGrpCod"
                        LEFT JOIN ATC1 PI ON PI."AbsEntry" = T0."AtcEntry" AND PI."Line" = 0
                        LEFT JOIN ATC1 PU ON PU."AbsEntry" = T0."AtcEntry" AND PU."Line" = 1
                        WHERE T0."ItemCode" = ?
                        '''
                        cur.execute(sql, (prod_code,))
                        row = cur.fetchone()
                        
                        if row:
                            # Build image URLs
                            img_file = row[7]
                            img_ext = row[8]
                            if img_file and img_ext:
                                product_image_url = f'/media/product_images/{folder_name}/{img_file}.{img_ext}'
                            else:
                                # Fallback to ItemCode-based naming
                                product_image_url = f'/media/product_images/{folder_name}/{prod_code}.jpg'
                            
                            urdu_file = row[9]
                            urdu_ext = row[10]
                            if urdu_file and urdu_ext:
                                urdu_url = f'/media/product_images/{folder_name}/{urdu_file}.{urdu_ext}'
                            else:
                                urdu_url = f'/media/product_images/{folder_name}/{prod_code}-urdu.jpg'
                            
                            product = {
                                'priority': idx,
                                'product_item_code': row[0],
                                'product_name': row[1],
                                'item_group_name': row[2],
                                'unit_of_measure': row[3] or row[4],
                                'generic_name': row[5],
                                'brand_name': row[6],
                                'product_image_url': product_image_url,
                                'product_description_urdu_url': urdu_url,
                                # Additional fields
                                'dosage': f'As per product label',
                                'application_method': 'Follow product instructions',
                                'timing': 'At first symptoms or preventively',
                            }
                            products_data.append(product)
                        
                        cur.close()
                        
                    except Exception as e:
                        logger.warning(f"Could not fetch product {prod_code}: {str(e)}")
                        continue
            
            return Response({
                'success': True,
                'disease_name': disease_info['disease_name'],
                'disease_item_code': disease_info['item_code'],
                'description': disease_info['description'],
                'database': hana_schema,
                'count': len(products_data),
                'data': products_data
            }, status=status.HTTP_200_OK)
            
        finally:
            conn.close()
        
    except Exception as e:
        logger.error(f"[RECOMMENDED_PRODUCTS] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

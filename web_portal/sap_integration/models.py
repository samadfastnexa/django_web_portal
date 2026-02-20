from django.db import models


class Policy(models.Model):
    """Stores policies derived from SAP Projects (UDF U_pol)."""
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    policy = models.CharField(max_length=255, blank=True, null=True)
    valid_from = models.DateField(blank=True, null=True)
    valid_to = models.DateField(blank=True, null=True)
    active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sap_integration_policy'
        verbose_name = 'Policy'
        verbose_name_plural = 'Policies'
        ordering = ['-updated_at']
        permissions = [
            ('manage_policies', 'Can manage policy records'),
        ]

    def __str__(self):
        return f"{self.code} - {self.policy or 'N/A'}"

class HanaConnect(models.Model):
    class Meta:
        db_table = 'sap_integration_hanaconnect'
        managed = False
        verbose_name = 'HANA Connect'
        verbose_name_plural = 'HANA Connect'
        permissions = [
            # Dashboard & General Access
            ('access_hana_connect', 'Can access HANA Connect dashboard'),
            ('post_to_sap', 'Can post data to SAP'),
            ('sync_policies', 'Can sync policies from SAP'),
            
            # Sales VS Achievement Reports
            ('view_sales_vs_achievement_geo', 'Can view Sales VS Achievement (Geo Inv)'),
            ('view_sales_vs_achievement_territory', 'Can view Sales VS Achievement (Territory)'),
            ('view_sales_vs_achievement_profit', 'Can view Sales VS Achievement (Profit)'),
            
            # Product & Policy
            ('view_products_catalog', 'Can view Products Catalog'),
            ('view_policy_balance', 'Can view Policy Wise Customer Balance'),
            ('view_policy_link', 'Can view and link policies'),
            
            # Territory & Organizational
            ('view_all_territories', 'Can view All Territories'),
            ('view_cwl', 'Can view CWL (Customer Watch List)'),
            
            # Sales Orders
            ('view_sales_orders', 'Can view Sales Orders'),
            ('create_sales_orders', 'Can create Sales Orders'),
            ('edit_sales_orders', 'Can edit Sales Orders'),
            
            # Master Data (List of Values)
            ('view_customer_list', 'Can view Customer List (LOV)'),
            ('view_item_master', 'Can view Item Master List'),
            ('view_project_list', 'Can view Project List'),
            ('view_crop_master', 'Can view Crop Master List'),
            ('view_tax_codes', 'Can view Sales Tax Codes'),
            
            # Customer & Contact Details
            ('view_customer_address', 'Can view Customer Address'),
            ('view_contact_person', 'Can view Contact Person Name'),
            ('view_child_customers', 'Can view Child Customers'),
            
            # Item & Warehouse
            ('view_warehouse_for_item', 'Can view Warehouse for Item'),
        ]

    def __str__(self):
        return 'HANA Connect'


class DiseaseIdentification(models.Model):
    """
    Stores disease identification data from SAP @ODID table.
    Maps diseases to their descriptions and metadata.
    """
    doc_entry = models.CharField(max_length=50, help_text="DocEntry from SAP @ODID table")
    item_code = models.CharField(max_length=100, unique=True, help_text="U_ItemCode - Disease identification code")
    item_name = models.CharField(max_length=255, help_text="U_ItemName - Disease name")
    description = models.TextField(blank=True, null=True, help_text="U_Description - Detailed disease description")
    disease_name = models.CharField(max_length=255, help_text="U_Disease - Disease scientific/common name")
    
    # Additional fields for better management
    is_active = models.BooleanField(default=True, help_text="Is this disease entry active?")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'sap_integration_diseaseidentification'
        verbose_name = 'Disease Identification'
        verbose_name_plural = 'Disease Identifications'
        ordering = ['disease_name', 'item_code']
        permissions = [
            ('view_disease_identification', 'Can view disease identifications'),
            ('manage_disease_identification', 'Can manage disease identifications'),
        ]
    
    def __str__(self):
        return f"{self.disease_name} ({self.item_code})"


class RecommendedProduct(models.Model):
    """
    Stores recommended products for specific diseases.
    Links diseases to product items with dosage and application instructions.
    """
    disease = models.ForeignKey(
        DiseaseIdentification,
        on_delete=models.CASCADE,
        related_name='recommended_products',
        help_text="Disease for which this product is recommended"
    )
    product_item_code = models.CharField(max_length=100, help_text="SAP Item Code of the recommended product (e.g., FG00259)")
    product_name = models.CharField(max_length=255, help_text="Product name")
    
    # Recommendation details
    dosage = models.CharField(max_length=255, blank=True, null=True, help_text="Recommended dosage (e.g., '500ml per acre')")
    application_method = models.TextField(blank=True, null=True, help_text="How to apply the product")
    timing = models.CharField(max_length=255, blank=True, null=True, help_text="When to apply (e.g., 'Early morning', 'At first symptoms')")
    precautions = models.TextField(blank=True, null=True, help_text="Safety precautions and warnings")
    
    # Priority and effectiveness
    priority = models.IntegerField(default=1, help_text="Recommendation priority (1=highest)")
    effectiveness_rating = models.DecimalField(
        max_digits=3, 
        decimal_places=1, 
        blank=True, 
        null=True,
        help_text="Effectiveness rating out of 10"
    )
    
    # Management fields
    is_active = models.BooleanField(default=True, help_text="Is this recommendation active?")
    notes = models.TextField(blank=True, null=True, help_text="Internal notes about this recommendation")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'sap_integration_recommendedproduct'
        verbose_name = 'Recommended Product'
        verbose_name_plural = 'Recommended Products'
        ordering = ['disease', 'priority', '-effectiveness_rating']
        unique_together = [['disease', 'product_item_code']]
        permissions = [
            ('view_recommended_product', 'Can view recommended products'),
            ('manage_recommended_product', 'Can manage recommended products'),
        ]
    
    def __str__(self):
        return f"{self.product_name} for {self.disease.disease_name} (Priority: {self.priority})"

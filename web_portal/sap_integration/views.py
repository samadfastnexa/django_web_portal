from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .sap_client import SAPClient
from FieldAdvisoryService.models import Dealer   # adjust import path


class SAPBusinessPartnerView(APIView):
    @swagger_auto_schema(
        operation_description="Fetch SAP Business Partner and sync local Dealer",
        manual_parameters=[
            openapi.Parameter(
                'card_code',
                openapi.IN_PATH,
                description='SAP CardCode',
                type=openapi.TYPE_STRING
            )
        ],
        responses={
            200: openapi.Response(
                description='SAP record + local dealer id',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'sap': openapi.Schema(type=openapi.TYPE_OBJECT),
                        'local': openapi.Schema(type=openapi.TYPE_INTEGER)
                    }
                )
            ),
            404: 'CardCode not found'
        },
        tags=['SAP']
    )
    def get(self, request, card_code):
        # ----------  quick debug ----------
        from preferences.models import Setting
        for s in Setting.objects.all():
            print(s.id, repr(s.slug), repr(s.value))
        try:
            Setting.objects.get(slug='sap_credential')
            print('sap_credential FOUND')
        except Setting.DoesNotExist:
            print('sap_credential NOT FOUND')
        # ----------  end debug ----------

        client = SAPClient()
        bp = client.get_bp(card_code)

        # 👇  add / update Dealer row here
        dealer, _ = Dealer.objects.update_or_create(
            card_code=card_code,
            defaults={
                'name': bp['CardName'],
                'address': bp.get('Address', ''),
                'contact_number': bp.get('Phone1', ''),
            }
        )
        return Response({'sap': bp, 'local': dealer.id})

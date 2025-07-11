from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from api.web3_config_payment import Createcomp, Createcompfree, Awardwinners, AwardWithPercentage , withdrawOwner , comptotal , compstatus , compexist , Awardforduel_comp , Awardforfree_comp , Awardforarbitrary_comp
from api.web3_config_payment import create_Tx_metamask
import json
import os

class CreateCompView(APIView):
    def post(self, request):
        try:
            ID = request.data.get('ID')
            Price = request.data.get('Price')
            if not ID or not Price:
                return Response({"error": "ID and Price are required."}, status=status.HTTP_400_BAD_REQUEST)

            tx_hash = Createcomp(ID, Price)
            return Response({"transaction_hash": tx_hash}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class CreateCompFreeView(APIView):
    def post(self, request):
        try:
            ID = request.data.get('ID')
            if not ID:
                return Response({"error": "ID is required."}, status=status.HTTP_400_BAD_REQUEST)

            tx_hash = Createcompfree(ID)
            return Response({"transaction_hash": tx_hash}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AwardWinnersView(APIView):
    def post(self, request):
        try:
            address_1 = request.data.get('address_1')
            address_2 = request.data.get('address_2')
            address_3 = request.data.get('address_3')
            ID = request.data.get('ID')

            if not address_1 or not address_2 or not address_3 or not ID:
                return Response({"error": "All addresses and ID are required."}, status=status.HTTP_400_BAD_REQUEST)

            tx_hash = Awardwinners(address_1, address_2, address_3, ID)
            return Response({"transaction_hash": tx_hash}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AwardWithPercentageView(APIView):
    def post(self, request):
        try:
            address_1 = request.data.get('address_1')
            address_2 = request.data.get('address_2')
            address_3 = request.data.get('address_3')
            percent_1 = request.data.get('percent_1')
            percent_2 = request.data.get('percent_2')
            percent_3 = request.data.get('percent_3')
            ID = request.data.get('ID')

            if not address_1 or not address_2 or not address_3 or not percent_1 or not percent_2 or not percent_3 or not ID:
                return Response({"error": "All addresses, percentages, and ID are required."}, status=status.HTTP_400_BAD_REQUEST)

            tx_hash = AwardWithPercentage(address_1, address_2, address_3, percent_1, percent_2, percent_3, ID)
            return Response({"transaction_hash": tx_hash}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class Awardforduel_comp(APIView):
    def post(self, request):
        try:
            address_1 = request.data.get('address_1')
            ID = request.data.get('ID')

            if not address_1 or not ID:
                return Response({"error": "addresses,and ID are required."}, status=status.HTTP_400_BAD_REQUEST)

            tx_hash = Awardforduel_comp(address_1, ID)
            return Response({"transaction_hash": tx_hash}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class Awardforfree_comp(APIView):
    def post(self, request):
        try:
            address_1 = request.data.get('address_1')
            address_2 = request.data.get('address_2')
            address_3 = request.data.get('address_3')
            value_1 = request.data.get('value_1')
            value_2 = request.data.get('value_2')
            value_3 = request.data.get('value_3')
            ID = request.data.get('ID')

            if not address_1 or not address_2 or not address_3 or not value_1 or not value_2 or not value_3 or not ID:
                return Response({"error": "All addresses, values, and ID are required."}, status=status.HTTP_400_BAD_REQUEST)

            tx_hash = Awardforfree_comp(address_1, address_2, address_3, value_1, value_2, value_3, ID)
            return Response({"transaction_hash": tx_hash}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class Awardforarbitrary_comp(APIView):
    def post(self, request):
        try:
            winners = request.data.get('winners', [])
            prizes = request.data.get('prizes', [])
            ID = request.data.get('ID')

            if not winners or not prizes or not ID:
                return Response({"error": "All addresseswinners, prizes, and ID are required."}, status=status.HTTP_400_BAD_REQUEST)

            tx_hash = Awardforarbitrary_comp( winners , prizes , ID)
            return Response({"transaction_hash": tx_hash}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class WithdrawWinnersView(APIView):
    def post(self, request):
        try:
            address = request.data.get('address')
            ID = request.data.get('ID')

            if not address or not ID:
                return Response({"error": "Address and ID are required."}, status=status.HTTP_400_BAD_REQUEST)

            tx_hash = withdrawOwner(address, ID)
            return Response({"transaction_hash": tx_hash}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CompTotalView(APIView):
    def get(self, request):
        try:
            ID = request.query_params.get('ID')
            if not ID:
                return Response({"error": "ID is required."}, status=status.HTTP_400_BAD_REQUEST)

            total = comptotal(ID)
            return Response({"total": total}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CompStatusView(APIView):
    def get(self, request):
        try:
            ID = request.query_params.get('ID')
            if not ID:
                return Response({"error": "ID is required."}, status=status.HTTP_400_BAD_REQUEST)

            status = compstatus(ID)
            return Response({"status": status}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class CompExistView(APIView):
    def get(self, request):
        try:
            ID = request.query_params.get('ID')
            if not ID:
                return Response({"error": "ID is required."}, status=status.HTTP_400_BAD_REQUEST)

            exist = compexist(ID)
            return Response({"exist": exist}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
# frontend view for creating a transaction using Metamask frontend send a post request with user_address and value
# and it will return the transaction hash with json format
class CreateTxView(APIView):
    def post(self, request):
        value = request.data.get('value')
        user_address = request.data.get('user_address')
        if not value or not user_address:
            return Response({'error': 'Value and user_address required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            tx = create_Tx_metamask(value, user_address)
            return Response(json.loads(tx))
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

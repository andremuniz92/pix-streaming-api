import random
import string
import logging
from datetime import datetime, timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import PixMessage
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils.crypto import get_random_string
from django.utils.timezone import now
from .models import PixMessage, StreamSession
from .serializers import PixMessageSerializer
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
import json

def random_string(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def random_cpf_cnpj():
    return ''.join(random.choices(string.digits, k=11))

logger = logging.getLogger(__name__)

class GeneratePixMessagesView(APIView):
    def post(self, request, ispb, number):
        try:
            number = int(number)
            if number <= 0:
                return Response({"error": "Number must be positive"}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError:
            return Response({"error": "Invalid number parameter"}, status=status.HTTP_400_BAD_REQUEST)

        for _ in range(number):
            PixMessage.objects.create(
                end_to_end_id=random_string(24),
                valor=round(random.uniform(1, 1000), 2),
                pagador_nome="Pagador " + random_string(5),
                pagador_cpf_cnpj=random_cpf_cnpj(),
                pagador_ispb=random_string(8),
                pagador_agencia=str(random.randint(1, 9999)).zfill(4),
                pagador_conta=random_string(7),
                pagador_tipo_conta=random.choice(['CACC', 'SVGS']),
                recebedor_nome="Recebedor " + random_string(5),
                recebedor_cpf_cnpj=random_cpf_cnpj(),
                recebedor_ispb=ispb,
                recebedor_agencia=str(random.randint(1, 9999)).zfill(4),
                recebedor_conta=random_string(7),
                recebedor_tipo_conta=random.choice(['CACC', 'SVGS']),
                campo_livre="",
                tx_id=random_string(16),
                data_pagamento=timezone.now()
            )

        return Response({"message": f"{number} Pix messages created for ISPB {ispb}"}, status=status.HTTP_201_CREATED)


class PixStreamStartView(APIView):
    def get(self, request, ispb):
        accept_header = request.headers.get('Accept', 'application/json').strip()
        logger.debug(f"Accept header: {accept_header}")
        is_multipart = accept_header == 'multipart/json'
        logger.debug(f"Is multipart: {is_multipart}")
        message_limit = 10 if is_multipart else 1
        logger.debug(f"Message limit: {message_limit}")

        # Verificar número de sessões ativas
        if StreamSession.objects.filter(ispb=ispb, active=True).count() >= 6:
            return Response({"detail": "Limite de streams ativos atingido."}, status=429)

        # Criar uma nova sessão
        interaction_id = get_random_string(12)
        session = StreamSession.objects.create(ispb=ispb)

        # Buscar mensagens disponíveis para esse ISPB
        messages = PixMessage.objects.filter(
            recebedor_ispb=ispb,
            claimed_by_stream__isnull=True
        )[:message_limit]

        if not messages:
            # Long polling: aguardar por novos dados
            session.delete()  # remove sessão vazia
            return Response(status=204, headers={'Pull-Next': f'/api/pix/{ispb}/stream/{interaction_id}'})

        with transaction.atomic():
            for msg in messages:
                msg.claimed_by_stream = session
                msg.save()

        # Serializando mensagens
        serialized = PixMessageSerializer(messages, many=True)

        # Cabeçalho Pull-Next
        response_headers = {
            'Pull-Next': f'/api/pix/{ispb}/stream/{interaction_id}'
        }

        # Se for multipart, preparar resposta com várias partes JSON
        if is_multipart:
            boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"  # Usar algum boundary único
            response = HttpResponse(content_type=f'multipart/mixed; boundary={boundary}')
            
            # Para garantir que a resposta seja bem formatada, vamos montar manualmente
            # Cada mensagem será uma parte separada no multipart
            response_content = ""

            for msg_data in serialized.data:
                # Escrevendo a parte do multipart para cada mensagem
                response_content += f"--{boundary}\r\n"
                response_content += f"Content-Type: application/json\r\n\r\n"
                response_content += json.dumps(msg_data)  # Cada mensagem serializada
                response_content += f"\r\n--{boundary}\r\n"

            # Finalizando a resposta multipart
            response_content += f"--{boundary}--\r\n"

            # Atribuindo o conteúdo final à resposta
            response.content = response_content

            return response

        # Caso contrário, responder com um JSON padrão
        return Response(
            data={"messages": serialized.data},
            status=200,
            headers=response_headers
        )
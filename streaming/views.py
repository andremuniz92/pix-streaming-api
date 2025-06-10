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
import time
from rest_framework.renderers import JSONRenderer
from .renderers import MultipartJsonRenderer

def random_string(length=10):
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))

def random_cpf_cnpj():
    return "".join(random.choices(string.digits, k=11))

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
                pagador_tipo_conta=random.choice(["CACC", "SVGS"]),
                recebedor_nome="Recebedor " + random_string(5),
                recebedor_cpf_cnpj=random_cpf_cnpj(),
                recebedor_ispb=ispb,
                recebedor_agencia=str(random.randint(1, 9999)).zfill(4),
                recebedor_conta=random_string(7),
                recebedor_tipo_conta=random.choice(["CACC", "SVGS"]),
                campo_livre="",
                tx_id=random_string(16),
                data_pagamento=timezone.now()
            )

        return Response({"message": f"{number} Pix messages created for ISPB {ispb}"}, status=status.HTTP_201_CREATED)


class PixStreamBaseView(APIView):
    renderer_classes = [MultipartJsonRenderer, JSONRenderer]

    def _get_messages_and_respond(self, request, ispb, interaction_id, check_session_limit=True):
        """
        Lógica comum para buscar mensagens e responder
        
        Args:
            request: Requisição HTTP
            ispb: ISPB da instituição
            interaction_id: ID de interação para o Pull-Next
            check_session_limit: Se deve verificar limite de sessões (True para start, False para continue)
        """
        is_multipart_requested = isinstance(request.accepted_renderer, MultipartJsonRenderer)
        message_limit = 10 if is_multipart_requested else 1

        # Verificar limite de sessões apenas para stream/start
        if check_session_limit:
            if StreamSession.objects.filter(ispb=ispb, active=True).count() >= 6:
                return Response({"detail": "Limite de streams ativos atingido."}, status=429)

            # Criar uma nova sessão apenas para stream/start
            session = StreamSession.objects.create(ispb=ispb)
        else:
            session = None

        # Buscar mensagens disponíveis para esse ISPB
        messages = PixMessage.objects.filter(
            recebedor_ispb=ispb,
            claimed_by_stream__isnull=True
        )[:message_limit]

        if not messages:
            # Long polling: aguardar por novos dados
            # Se a sessão foi criada nesta requisição e não há mensagens, removê-la
            if session:
                session.delete()
            
            time.sleep(8)
            response = HttpResponse(status=204)
            response["Pull-Next"] = f"/api/pix/{ispb}/stream/{interaction_id}"
            response["Content-Length"] = "0"
            return response

        # Se há mensagens e temos uma sessão, associar as mensagens à sessão
        if session:
            with transaction.atomic():
                for msg in messages:
                    msg.claimed_by_stream = session
                    msg.save()

        # Serializando mensagens
        serialized = PixMessageSerializer(messages, many=True)

        # Gerar novo interaction_id para o próximo Pull-Next
        new_interaction_id = get_random_string(12)
        response_headers = {
            "Pull-Next": f"/api/pix/{ispb}/stream/{new_interaction_id}"
        }

        # Se multipart/json foi solicitado, retorna o array diretamente
        if is_multipart_requested:
            response_content = json.dumps(serialized.data)
            response = HttpResponse(response_content, content_type="application/json", status=200)
            for header, value in response_headers.items():
                response[header] = value
            return response
        else:
            # Para application/json ou default, usa Response do DRF
            return Response(
                data=serialized.data[0] if serialized.data else {},
                status=200,
                headers=response_headers
            )


class PixStreamStartView(PixStreamBaseView):
    """Endpoint para iniciar um stream de mensagens Pix"""

    def get(self, request, ispb):
        interaction_id = get_random_string(12)
        return self._get_messages_and_respond(request, ispb, interaction_id, check_session_limit=True)


class PixStreamContinueDeleteView(PixStreamBaseView):
    """Endpoint para continuar ou finalizar um stream de mensagens Pix"""

    def get(self, request, ispb, interaction_id):
        """Continuar um stream de mensagens Pix existente"""
        # Para continuação, não verificamos limite de sessões nem criamos nova sessão
        return self._get_messages_and_respond(request, ispb, interaction_id, check_session_limit=False)

    def delete(self, request, ispb, interaction_id):
        """Finalizar um stream de mensagens Pix"""
        # Buscar sessões ativas para este ISPB
        active_sessions = StreamSession.objects.filter(ispb=ispb, active=True)
        
        if active_sessions.exists():
            # Marcar a primeira sessão ativa como inativa
            session_to_deactivate = active_sessions.first()
            session_to_deactivate.active = False
            session_to_deactivate.save()
            
            logger.info(f"Stream finalizado para ISPB {ispb}, interaction_id {interaction_id}")
        else:
            # Mesmo se não houver sessões ativas, retornamos 200 (idempotência)
            logger.info(f"Tentativa de finalizar stream inexistente para ISPB {ispb}, interaction_id {interaction_id}")

        # Retornar 200 OK com corpo vazio conforme especificação
        return Response({}, status=200)
    

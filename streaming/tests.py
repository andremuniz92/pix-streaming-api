from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from .models import PixMessage, StreamSession
from django.utils.crypto import get_random_string
from django.utils import timezone
import json
import time
from unittest.mock import patch


class PixStreamAPITests(APITestCase):
    """Testes de integração para a API de streaming Pix"""

    def setUp(self):
        """Configuração inicial para cada teste"""
        self.ispb = "12345678"
        self.start_url = f"/api/pix/{self.ispb}/stream/start"
        
        # Limpar sessões e mensagens antes de cada teste para garantir um estado limpo
        StreamSession.objects.all().delete()
        PixMessage.objects.all().delete()

    def _create_pix_messages(self, count=1, ispb=None):
        """Helper para criar mensagens Pix para os testes"""
        if ispb is None:
            ispb = self.ispb
        messages = []
        for i in range(count):
            messages.append(PixMessage.objects.create(
                end_to_end_id=f"E{ispb}2024{get_random_string(10)}",
                valor=round(100.00 + i, 2),
                pagador_nome=f"Test Pagador {i}",
                pagador_cpf_cnpj="11122233344",
                pagador_ispb="00000000",
                pagador_agencia="0001",
                pagador_conta="1234567",
                pagador_tipo_conta="CACC",
                recebedor_nome=f"Test Recebedor {i}",
                recebedor_cpf_cnpj="55566677788",
                recebedor_ispb=ispb,
                recebedor_agencia="0002",
                recebedor_conta="7654321",
                recebedor_tipo_conta="SVGS",
                campo_livre="",
                tx_id=get_random_string(16),
                data_pagamento=timezone.now()
            ))
        return messages

    def _extract_interaction_id_from_pull_next(self, pull_next_header):
        """Extrai o interaction_id do cabeçalho Pull-Next"""
        # Pull-Next format: "/api/pix/12345678/stream/ABC123DEF456"
        return pull_next_header.split('/')[-1]

    def _get_response_data(self, response):
        """Helper para extrair dados da resposta, lidando com HttpResponse e Response do DRF"""
        if hasattr(response, 'data'):
            # Response do DRF
            return response.data
        else:
            # HttpResponse - precisa fazer parse do JSON
            return json.loads(response.content.decode('utf-8'))

    # ==================== TESTES PARA STREAM/START ====================

    def test_start_stream_application_json_single_message(self):
        """Teste: GET /stream/start com Accept: application/json deve retornar uma única mensagem"""
        self._create_pix_messages(count=3)
        
        response = self.client.get(self.start_url, HTTP_ACCEPT="application/json")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Pull-Next", response.headers)
        
        # Para application/json, deve retornar um objeto (não array)
        data = self._get_response_data(response)
        self.assertIsInstance(data, dict)
        self.assertIn("endToEndId", data)
        self.assertIn("valor", data)

    def test_start_stream_multipart_json_multiple_messages(self):
        """Teste: GET /stream/start com Accept: multipart/json deve retornar múltiplas mensagens"""
        self._create_pix_messages(count=5)
        
        response = self.client.get(self.start_url, HTTP_ACCEPT="multipart/json")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Pull-Next", response.headers)
        
        # Para multipart/json, deve retornar um array
        data = self._get_response_data(response)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 5)
        self.assertIn("endToEndId", data[0])

    @patch('streaming.views.time.sleep')  # Mock do sleep para acelerar o teste
    def test_start_stream_no_messages_returns_204(self, mock_sleep):
        """Teste: GET /stream/start sem mensagens deve retornar 204 após long polling"""
        # Não criar mensagens
        
        response = self.client.get(self.start_url, HTTP_ACCEPT="application/json")
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertIn("Pull-Next", response.headers)
        mock_sleep.assert_called_once_with(8)  # Verifica se o long polling foi executado

    def test_start_stream_session_limit_reached(self):
        """Teste: GET /stream/start deve retornar 429 quando limite de 6 sessões é atingido"""
        # Criar 6 sessões ativas
        for i in range(6):
            StreamSession.objects.create(ispb=self.ispb, active=True)
        
        response = self.client.get(self.start_url, HTTP_ACCEPT="application/json")
        
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        data = self._get_response_data(response)
        self.assertIn("Limite de streams ativos atingido", data["detail"])

    def test_start_stream_multipart_respects_10_message_limit(self):
        """Teste: GET /stream/start com multipart/json deve respeitar limite de 10 mensagens"""
        self._create_pix_messages(count=15)  # Criar mais que o limite
        
        response = self.client.get(self.start_url, HTTP_ACCEPT="multipart/json")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = self._get_response_data(response)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 10)  # Deve retornar apenas 10

    # ==================== TESTES PARA STREAM/CONTINUE ====================

    def test_continue_stream_application_json(self):
        """Teste: GET /stream/{id} com Accept: application/json"""
        self._create_pix_messages(count=2)
        interaction_id = "test123"
        continue_url = f"/api/pix/{self.ispb}/stream/{interaction_id}"
        
        response = self.client.get(continue_url, HTTP_ACCEPT="application/json")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Pull-Next", response.headers)
        data = self._get_response_data(response)
        self.assertIsInstance(data, dict)

    def test_continue_stream_multipart_json(self):
        """Teste: GET /stream/{id} com Accept: multipart/json"""
        self._create_pix_messages(count=5)
        interaction_id = "test456"
        continue_url = f"/api/pix/{self.ispb}/stream/{interaction_id}"
        
        response = self.client.get(continue_url, HTTP_ACCEPT="multipart/json")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Pull-Next", response.headers)
        data = self._get_response_data(response)
        self.assertIsInstance(data, list)

    def test_continue_stream_no_session_limit_check(self):
        """Teste: GET /stream/{id} não deve verificar limite de sessões"""
        # Criar 6 sessões ativas (que bloquearia stream/start)
        for i in range(6):
            StreamSession.objects.create(ispb=self.ispb, active=True)
        
        self._create_pix_messages(count=1)
        interaction_id = "test789"
        continue_url = f"/api/pix/{self.ispb}/stream/{interaction_id}"
        
        response = self.client.get(continue_url, HTTP_ACCEPT="application/json")
        
        # Deve funcionar mesmo com 6 sessões ativas
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # ==================== TESTES PARA DELETE ====================

    def test_delete_stream_success(self):
        """Teste: DELETE /stream/{id} deve retornar 200 e finalizar sessão"""
        # Criar uma sessão ativa
        session = StreamSession.objects.create(ispb=self.ispb, active=True)
        interaction_id = "delete123"
        delete_url = f"/api/pix/{self.ispb}/stream/{interaction_id}"
        
        response = self.client.delete(delete_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = self._get_response_data(response)
        self.assertEqual(data, {})
        
        # Verificar se a sessão foi marcada como inativa
        session.refresh_from_db()
        self.assertFalse(session.active)

    def test_delete_stream_no_active_sessions(self):
        """Teste: DELETE /stream/{id} deve retornar 200 mesmo sem sessões ativas (idempotência)"""
        interaction_id = "delete456"
        delete_url = f"/api/pix/{self.ispb}/stream/{interaction_id}"
        
        response = self.client.delete(delete_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = self._get_response_data(response)
        self.assertEqual(data, {})

    # ==================== TESTES DE FLUXO COMPLETO ====================

    def test_complete_stream_flow(self):
        """Teste: Fluxo completo start → continue → delete"""
        self._create_pix_messages(count=3)
        
        # 1. Iniciar stream
        start_response = self.client.get(self.start_url, HTTP_ACCEPT="application/json")
        self.assertEqual(start_response.status_code, status.HTTP_200_OK)
        
        # 2. Extrair interaction_id do Pull-Next
        pull_next = start_response.headers["Pull-Next"]
        interaction_id = self._extract_interaction_id_from_pull_next(pull_next)
        
        # 3. Continuar stream
        continue_url = f"/api/pix/{self.ispb}/stream/{interaction_id}"
        continue_response = self.client.get(continue_url, HTTP_ACCEPT="application/json")
        self.assertEqual(continue_response.status_code, status.HTTP_200_OK)
        
        # 4. Finalizar stream
        delete_response = self.client.delete(continue_url)
        self.assertEqual(delete_response.status_code, status.HTTP_200_OK)
        data = self._get_response_data(delete_response)
        self.assertEqual(data, {})

    def test_session_limit_after_delete(self):
        """Teste: Após DELETE, deve ser possível criar novos streams"""
        # Criar 6 sessões ativas para atingir o limite
        sessions = []
        for i in range(6):
            sessions.append(StreamSession.objects.create(ispb=self.ispb, active=True))
        
        # Tentar iniciar stream (deve falhar)
        response = self.client.get(self.start_url, HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        
        # Finalizar um stream via DELETE
        delete_url = f"/api/pix/{self.ispb}/stream/test123"
        delete_response = self.client.delete(delete_url)
        self.assertEqual(delete_response.status_code, status.HTTP_200_OK)
        
        # Agora deve ser possível iniciar um novo stream
        self._create_pix_messages(count=1)
        response = self.client.get(self.start_url, HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_different_ispb_isolation(self):
        """Teste: Mensagens de ISPBs diferentes devem ser isoladas"""
        ispb1 = "11111111"
        ispb2 = "22222222"
        
        # Criar mensagens para dois ISPBs diferentes
        self._create_pix_messages(count=2, ispb=ispb1)
        self._create_pix_messages(count=3, ispb=ispb2)
        
        # Buscar mensagens para ISPB1
        url1 = f"/api/pix/{ispb1}/stream/start"
        response1 = self.client.get(url1, HTTP_ACCEPT="multipart/json")
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        data1 = self._get_response_data(response1)
        self.assertEqual(len(data1), 2)
        
        # Buscar mensagens para ISPB2
        url2 = f"/api/pix/{ispb2}/stream/start"
        response2 = self.client.get(url2, HTTP_ACCEPT="multipart/json")
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        data2 = self._get_response_data(response2)
        self.assertEqual(len(data2), 3)

    def test_message_claimed_by_stream_not_duplicated(self):
        """Teste: Mensagens já claimed não devem aparecer em outros streams"""
        self._create_pix_messages(count=2)
        
        # Primeiro stream pega as mensagens
        response1 = self.client.get(self.start_url, HTTP_ACCEPT="multipart/json")
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        data1 = self._get_response_data(response1)
        self.assertEqual(len(data1), 2)
        
        # Segundo stream não deve pegar as mesmas mensagens
        response2 = self.client.get(self.start_url, HTTP_ACCEPT="multipart/json")
        self.assertEqual(response2.status_code, status.HTTP_204_NO_CONTENT)


class PixStreamUnitTests(APITestCase):
    """Testes unitários para componentes específicos"""

    def test_random_string_length(self):
        """Teste: random_string deve gerar string com tamanho correto"""
        from .views import random_string
        
        result = random_string(10)
        self.assertEqual(len(result), 10)
        self.assertTrue(result.isalnum())

    def test_random_cpf_cnpj_format(self):
        """Teste: random_cpf_cnpj deve gerar string numérica com 11 dígitos"""
        from .views import random_cpf_cnpj
        
        result = random_cpf_cnpj()
        self.assertEqual(len(result), 11)
        self.assertTrue(result.isdigit())

    def test_pix_message_model_creation(self):
        """Teste: Criação de PixMessage com campos obrigatórios"""
        message = PixMessage.objects.create(
            end_to_end_id="E123456789",
            valor=100.50,
            pagador_nome="Test Pagador",
            pagador_cpf_cnpj="12345678901",
            pagador_ispb="12345678",
            pagador_agencia="0001",
            pagador_conta="123456",
            pagador_tipo_conta="CACC",
            recebedor_nome="Test Recebedor",
            recebedor_cpf_cnpj="98765432109",
            recebedor_ispb="87654321",
            recebedor_agencia="0002",
            recebedor_conta="654321",
            recebedor_tipo_conta="SVGS",
            campo_livre="",
            tx_id="TX123456",
            data_pagamento=timezone.now()
        )
        
        self.assertIsNotNone(message.id)
        self.assertEqual(message.valor, 100.50)
        self.assertEqual(message.pagador_nome, "Test Pagador")

    def test_stream_session_model_creation(self):
        """Teste: Criação de StreamSession"""
        session = StreamSession.objects.create(ispb="12345678")
        
        self.assertIsNotNone(session.id)
        self.assertEqual(session.ispb, "12345678")
        self.assertTrue(session.active)  # Deve ser True por padrão


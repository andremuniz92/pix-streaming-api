import uuid
from django.db import models

class PixMessage(models.Model):
    end_to_end_id = models.CharField(max_length=100, unique=True)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    
    pagador_nome = models.CharField(max_length=100)
    pagador_cpf_cnpj = models.CharField(max_length=14)
    pagador_ispb = models.CharField(max_length=8)
    pagador_agencia = models.CharField(max_length=10)
    pagador_conta = models.CharField(max_length=20)
    pagador_tipo_conta = models.CharField(max_length=10)

    recebedor_nome = models.CharField(max_length=100)
    recebedor_cpf_cnpj = models.CharField(max_length=14)
    recebedor_ispb = models.CharField(max_length=8)
    recebedor_agencia = models.CharField(max_length=10)
    recebedor_conta = models.CharField(max_length=20)
    recebedor_tipo_conta = models.CharField(max_length=10)

    campo_livre = models.TextField(blank=True)
    tx_id = models.CharField(max_length=100)
    data_pagamento = models.DateTimeField()

    claimed = models.BooleanField(default=False)
    claimed_by_stream = models.ForeignKey('StreamSession', null=True, blank=True, on_delete=models.SET_NULL, related_name='messages')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.end_to_end_id


class StreamSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ispb = models.CharField(max_length=8)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_pull_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.ispb} - {self.id}"


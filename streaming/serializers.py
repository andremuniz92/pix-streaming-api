from rest_framework import serializers
from .models import PixMessage
from .models import StreamSession

class PixMessageSerializer(serializers.ModelSerializer):
    pagador = serializers.SerializerMethodField()
    recebedor = serializers.SerializerMethodField()
    endToEndId = serializers.CharField(source='end_to_end_id')
    valor = serializers.DecimalField(max_digits=10, decimal_places=2)
    txId = serializers.CharField(source='tx_id')
    dataHoraPagamento = serializers.DateTimeField(source='data_pagamento')
    campoLivre = serializers.CharField(source='campo_livre')

    class Meta:
        model = PixMessage
        fields = [
            'endToEndId', 'valor', 'pagador', 'recebedor',
            'campoLivre', 'txId', 'dataHoraPagamento'
        ]

    def get_pagador(self, obj):
        return {
            "nome": obj.pagador_nome,
            "cpfCnpj": obj.pagador_cpf_cnpj,
            "ispb": obj.pagador_ispb,
            "agencia": obj.pagador_agencia,
            "contaTransacional": obj.pagador_conta,
            "tipoConta": obj.pagador_tipo_conta,
        }

    def get_recebedor(self, obj):
        return {
            "nome": obj.recebedor_nome,
            "cpfCnpj": obj.recebedor_cpf_cnpj,
            "ispb": obj.recebedor_ispb,
            "agencia": obj.recebedor_agencia,
            "contaTransacional": obj.recebedor_conta,
            "tipoConta": obj.recebedor_tipo_conta,
        }


class StreamSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = StreamSession
        fields = ['id', 'ispb', 'created_at']
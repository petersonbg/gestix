from django.db.models.signals import post_delete, post_save

from caixa.models import Caixa, MovimentacaoCaixa
from contas_pagar.models import ContaPagar
from contas_receber.models import ContaReceber
from produtos.models import Produto
from vendas.models import ItemVenda, Venda

from .cache import invalidar_cache_dashboard


MODELOS_DASHBOARD = (
    Caixa,
    MovimentacaoCaixa,
    ContaPagar,
    ContaReceber,
    Produto,
    Venda,
    ItemVenda,
)


for modelo in MODELOS_DASHBOARD:
    post_save.connect(
        invalidar_cache_dashboard,
        sender=modelo,
        dispatch_uid=f'dashboard_cache_save_{modelo._meta.label_lower}',
        weak=False,
    )
    post_delete.connect(
        invalidar_cache_dashboard,
        sender=modelo,
        dispatch_uid=f'dashboard_cache_delete_{modelo._meta.label_lower}',
        weak=False,
    )
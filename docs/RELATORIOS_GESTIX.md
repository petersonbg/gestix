# Relatorios Basicos do GESTIX

O modulo `relatorios` centraliza consultas essenciais para acompanhamento da empresa antes da implantacao em producao.

## Permissoes

| Relatorio | Administrador | Gerente | Vendedor | Estoquista |
|---|---:|---:|---:|---:|
| Vendas por Periodo | Sim | Sim | Sim | Nao |
| Estoque Baixo | Sim | Sim | Nao | Sim |
| Contas a Receber | Sim | Sim | Nao | Nao |
| Contas a Pagar | Sim | Sim | Nao | Nao |
| Caixa Diario | Sim | Sim | Nao | Nao |

Usuarios sem perfil nao acessam o modulo.

## Relatorios

### Vendas por Periodo

URL: `/relatorios/vendas/`

Filtros: data inicial, data final, cliente, vendedor, forma de pagamento, status e opcao para incluir canceladas.

Por padrao considera somente vendas finalizadas.

### Estoque Baixo

URL: `/relatorios/estoque-baixo/`

Lista produtos com `estoque_atual <= estoque_minimo`.

Filtros: categoria, fornecedor e status ativo/inativo.

### Contas a Receber

URL: `/relatorios/contas-receber/`

Filtros: data inicial, data final, cliente, status e vencimento.

Resumo: total em aberto, total recebido, total atrasado e quantidade de parcelas atrasadas.

### Contas a Pagar

URL: `/relatorios/contas-pagar/`

Filtros: data inicial, data final, fornecedor, categoria, status e vencimento.

Resumo: total em aberto, total pago, total atrasado e contas vencendo nos proximos 7 dias.

### Caixa Diario

URL: `/relatorios/caixa-diario/`

Filtros: data, usuario e status.

Resumo: caixas abertos/fechados, total vendido, total em dinheiro, PIX, cartao e diferenca total.

## Impressao e CSV

Todos os relatorios possuem botoes:

- `Imprimir`: abre template A4 retrato com cabecalho da empresa, usuario emissor e data/hora.
- `Exportar CSV`: baixa arquivo `.csv` com separador `;`.

As acoes de emissao, impressao e CSV sao registradas em `LogAtividade` quando disponivel.

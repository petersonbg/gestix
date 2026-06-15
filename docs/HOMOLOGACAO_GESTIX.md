# Checklist de Homologação do GESTIX

Data de abertura: **15/06/2026**  
Legenda: **Pendente** = depende de execução/validação; **OK** = verificado; **Corrigir** = falha confirmada.

> Este documento registra a fase de homologação. Marque o status somente após executar o cenário em ambiente equivalente ao de implantação e preencha evidências nas observações.

## 1. Estrutura e ambiente

| Verificação | Resultado esperado | Status | Observações |
|---|---|---|---|
| Apps instalados | Todos os módulos em `INSTALLED_APPS` | OK | Revisão estática concluída |
| URLs | Rotas principais e admin carregadas | OK | Revisão estática concluída |
| Templates | Templates referenciados existem | OK | Estrutura revisada |
| Staticfiles | `collectstatic` sem erro e assets acessíveis | Pendente | Django/dependências indisponíveis no executor |
| Migrations | Sem alterações de model pendentes | Pendente | Executar `makemigrations --check` |
| Settings e `.env` | Configuração externa, hosts, CSRF e mídia coerentes | OK | URL de mídia e modo LAN revisados |
| Docker Compose | Web/DB saudáveis e volume persistente | Pendente | Docker indisponível no executor |

## 2. Verificações automatizadas obrigatórias

| Comando | Resultado esperado | Status | Observações |
|---|---|---|---|
| `python manage.py check` | Sem erros | Pendente | Django não instalado; instalação bloqueada pela rede |
| `python manage.py makemigrations --check` | “No changes detected” | Pendente | Mesma limitação |
| `python manage.py migrate` | Todas as migrations aplicadas | Pendente | Requer PostgreSQL/Django |
| `python manage.py test` | Suíte integral aprovada | Pendente | Requer dependências |
| `python -m compileall ...` | Fontes Python compilam | OK | Executado na homologação |

## 3. Checklist funcional por módulo

### Clientes

| Cenário | Resultado esperado | Status | Observações |
|---|---|---|---|
| Cadastrar/editar/buscar | Persistência e busca corretas | Pendente | |
| CPF/CNPJ | Formato e regra de negócio validados | Pendente | |
| Inscrição estadual/data de nascimento | Campos preservados | Pendente | |

### Produtos

| Cenário | Resultado esperado | Status | Observações |
|---|---|---|---|
| Cadastro e código automático | Código único sequencial | Pendente | |
| Preço de custo opcional | Vazio tratado como zero | Pendente | |
| Categoria e filtro | Apenas categorias válidas; filtro combinável | Pendente | |
| Chassi | Persistido somente para veículos | Pendente | |
| Estoque mínimo | Alerta/campo consistente | Pendente | |

### Fornecedores

| Cenário | Resultado esperado | Status | Observações |
|---|---|---|---|
| Cadastrar/editar/buscar | Fluxos sem perda de dados | Pendente | |

### Estoque

| Cenário | Resultado esperado | Status | Observações |
|---|---|---|---|
| Entrada/saída/ajuste | Saldo e histórico consistentes | Pendente | |
| Saída acima do saldo | Operação recusada no backend | Pendente | |

### Vendas

| Cenário | Resultado esperado | Status | Observações |
|---|---|---|---|
| Pesquisar cliente/produto | Resultados relevantes e ativos | Pendente | Correspondência exata de cliente priorizada |
| Finalizar/cancelar rascunho | Estados e integrações consistentes | Pendente | |
| Venda sem estoque | Recusada no backend | Pendente | |
| Crediário | Parcelas geradas corretamente | Pendente | |
| Recibo | A5 14×21 cm retrato, legível | Pendente | Validar Chrome, Edge e Firefox |

### Caixa

| Cenário | Resultado esperado | Status | Observações |
|---|---|---|---|
| Abrir/suprimento/sangria/saída | Movimentos e saldo corretos | Pendente | |
| Venda e fechamento | Valores e diferença corretos | Pendente | |

### Orçamentos

| Cenário | Resultado esperado | Status | Observações |
|---|---|---|---|
| Cliente e produtos | Inclusão e totais corretos | Pendente | |
| Impressão | A5 e frase “ORÇAMENTO VÁLIDO POR 30 DIAS” | Pendente | |
| Converter em venda | Dados transferidos sem duplicação | Pendente | |

### Ordens de Serviço

| Cenário | Resultado esperado | Status | Observações |
|---|---|---|---|
| Cadastro/cliente/serviço dropdown | Somente serviços ativos | Pendente | |
| Produtos/deslocamento/desconto | Total correto e estoque íntegro | Pendente | |
| Responsáveis, assinatura e conclusão | Dados exibidos e edição final bloqueada | Pendente | |
| Impressão | A5, assinaturas compactas e conteúdo íntegro | Pendente | |

### Contas a Receber

| Cenário | Resultado esperado | Status | Observações |
|---|---|---|---|
| Parcelas/recebimento | Baixa e caixa consistentes | Pendente | |
| Caixa obrigatório | Recebimento bloqueado quando aplicável | Pendente | |
| Atrasos no dashboard | Valores e datas corretos | Pendente | |

### Contas a Pagar

| Cenário | Resultado esperado | Status | Observações |
|---|---|---|---|
| Cadastrar/pagar/cancelar | Estado e caixa consistentes | Pendente | |
| Alertas no dashboard | Vencimentos corretos | Pendente | |

### Administração

| Cenário | Resultado esperado | Status | Observações |
|---|---|---|---|
| Dados da empresa/logotipos | Upload válido e mídia acessível | Pendente | Validador não falha em arquivo já persistido |
| Categorias/serviços | CRUD conforme perfil | Pendente | |
| Configurações | Aniversários e logout aplicados | Pendente | |

## 4. Impressões

| Documento | Resultado esperado | Status | Observações |
|---|---|---|---|
| Recibo de venda | 140×210 mm, retrato, assinatura centralizada | Pendente | Testar até 20 itens |
| Ordem de serviço | 140×210 mm, assinaturas lado a lado | Pendente | Testar serviços e produtos |
| Orçamento | 140×210 mm, validade e totais legíveis | Pendente | Testar até 20 itens |
| Cabeçalho | Endereço em uma linha e contato visível | Pendente | |

## 5. Permissões e segurança

| Cenário | Resultado esperado | Status | Observações |
|---|---|---|---|
| Administrador/Gerente/Vendedor/Estoquista | Acesso e botões conforme perfil | Pendente | Validar também POST direto |
| Login/CSRF | Rotas protegidas e POST com CSRF | Pendente | Middleware presente; requer teste integrado |
| Logout por inatividade/cache | Sessão encerrada e páginas privadas não reutilizadas | Pendente | |
| Venda/OS finalizada | Edição bloqueada no backend | Pendente | |
| Estoque | Validação concorrente no backend | Pendente | |

## 6. Docker, persistência e recuperação

| Cenário | Resultado esperado | Status | Observações |
|---|---|---|---|
| `docker compose up -d --build` | Web e DB saudáveis | Pendente | Docker indisponível neste executor |
| Migrate/collectstatic | Inicialização sem erro | Pendente | |
| Reinício | Banco preservado no volume | Pendente | |
| Backup/restauração | SQL gerado e restaurado em banco de teste | Pendente | Scripts corrigidos; validar em Windows |
| Mídia | Logos/assinaturas acessíveis com DEBUG=False | Pendente | `SERVE_MEDIA_FILES=True` para rede local |

## 7. Critérios de aceite

A implantação somente deve ser autorizada quando:

1. todos os comandos obrigatórios estiverem **OK**;
2. não houver pendência de prioridade crítica ou alta;
3. backup e restauração forem comprovados em banco descartável;
4. os quatro perfis forem testados no frontend e por requisição direta;
5. as três impressões forem aprovadas nos navegadores-alvo;
6. segredos, senha do banco, hosts e HTTPS estiverem configurados para o ambiente real.

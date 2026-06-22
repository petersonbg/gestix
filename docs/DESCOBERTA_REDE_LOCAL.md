# Descoberta automatica do GESTIX

O servidor iniciado pelo launcher nao depende de IP fixo nem de configuracao do
roteador. O nome real da maquina e detectado automaticamente.

- acesso principal: `http://HOSTNAME:PORTA`;
- mDNS/DNS-SD: hostname `HOSTNAME.local` e servico `_gestix._tcp.local.`;
- broadcast UDP: fallback na porta `37020/UDP`.

O launcher detecta o IPv4 atual, inclui `gestix.local` e esse endereco nas
configuracoes do Django, inicia o Waitress e mantem o processo de descoberta
ativo. No Windows, ele tenta liberar no perfil de rede privada:

- porta HTTP escolhida pelo launcher em TCP;
- porta `5353/UDP` para mDNS;
- porta `37020/UDP` para o fallback.

## Servidor

Inicie normalmente:

```bat
GESTIX.exe
```

Ou como servico:

```bat
GESTIX.exe --service
```

A janela e `logs/launcher_diagnostico.txt` exibem o nome da maquina, hostname,
IP atual, porta e URL recomendada.

## Computadores clientes

Os clientes nao precisam instalar o GESTIX nem executar um aplicativo. Basta
abrir no navegador o endereco exibido pelo launcher ou pelo dashboard:

```text
http://HOSTNAME:8000
```

Em redes com mDNS, tambem pode ser usado:

```text
http://HOSTNAME.local:8000
```

O dashboard administrativo mostra o endereco de acesso e uma pagina de
diagnostico em `Administracao > Diagnostico de Rede`.

## Limites da rede local

Os dispositivos precisam estar na mesma LAN e a rede nao pode ter isolamento
entre clientes, como ocorre em algumas redes Wi-Fi de convidados. Nao e
necessario reservar IP, alterar DNS ou criar encaminhamento de porta no
roteador.

# FSE_Trabalho_1

Repositório para o [trabalho 1](https://gitlab.com/fse_fga/trabalhos-2022_2/trabalho-1-2022-2) da disciplina de Fundamentos de Sistemas Embarcados (FGA-UnB).

# Servidor central

## Dependências

* python3 (versão utilizada nos testes: 3.7.3)

## Como executar

Para rodar o servidor central:

```bash
python3 server.py <ip> <porta>
```

**Obs:** ```<ip>``` e ```<porta>``` utilizado por padrão no arquivo de configuração (**[config.json](/config.json)**) do servidor distribuído é respectivamente **164.41.98.15** e ***10590***

Para rodar um servidor distribuído:

```bash
python3 client.py
```


## Funcionamento

Após executar o servidor central estará a espera dos dois servidores distribuídos conectarem ao ```<ip>``` ```<porta>``` escolhida.

Após um servidor distribuído se conectar, o usuário poderá:

* selecionar um servidor distribuído (sala) para qual deseja enviar um comando
* ligar/desligar os dispostivos ao pressionar a tecla correspondente ao comando como é apresentado na interface
* ligar o alarme de segurança teclando a tecla **'a'**.
* desligar o alarme de segurança teclando a tecla **'p'**.
* Para sair pressione **'Esc'** e então **'Ctrl+C''**.
* Um linha de log e gerado no arquivo **log.csv** para cada comando enviado pelo usuário ou acionamento de alarme


## Funcionamento

Não há ordem para execução dos servidores, logo pode iniciar com o distribuído ou com o central

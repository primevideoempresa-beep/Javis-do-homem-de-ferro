# Javis AI — Windows

Esta pasta é a ponte que deixa o Javis controlar o PC. É a ponte padrão do projeto: o
firmware (`javis.ino`) já chama `http://127.0.0.1:8766` diretamente, nesta pasta.

## Configurar

Abra `javis_windows.py` e troque `JAVIS_ORIGIN` pelo IP do seu Javis (o OLED mostra o IP
por 3 segundos ao ligar). Só a página servida por esse IP pode pedir ações pelo navegador;
chamadas locais (o painel, os testes) continuam liberadas.

## Iniciar

No Windows, execute:

```bat
windows\start_javis_windows.bat
```

Ou manualmente:

```bat
py windows\javis_windows.py
py windows\painel_javis.py
```

O servidor local fica em `http://127.0.0.1:8766`.

## Comandos disponíveis

- Abrir apps permitidos: Notepad, Paint, Calculadora, Explorer, VS Code, Arduino, Chrome, Edge, WhatsApp.
- Abrir sites: Google, YouTube, Gmail, Drive, Agenda, GitHub, ChatGPT, Instagram, Facebook, WhatsApp Web.
- Pesquisar em Google, YouTube ou Bing.
- Bloquear, suspender, reiniciar e desligar o Windows; cancelar desligamento agendado.
- Informações do computador.
- Abrir/criar/copiar/mover arquivos somente dentro da pasta do usuário.
- Criar e abrir uma página HTML local.
- Copiar texto para o clipboard.
- Preparar texto para WhatsApp sem envio automático.

## Segurança

- Não existe endpoint para executar comando arbitrário. Entradas de usuário não são concatenadas em comandos de shell.
- Só a origem configurada em `JAVIS_ORIGIN` pode chamar a ponte pelo navegador; outras páginas recebem "origem não autorizada".
- O WhatsApp nunca envia sozinho: `wa_draft` só copia o texto para o clipboard e abre o app. Colar e enviar é sempre manual.
- Ações destrutivas ou sensíveis (desligar, reiniciar) devem continuar exigindo confirmação na interface.

## Integração com o ESP32

O firmware (`javis.ino`) já chama `http://127.0.0.1:8766` diretamente — funciona quando o
ESP32 e o navegador que abre a página do Javis estão na mesma rede que este PC. Como o Chrome
trata `127.0.0.1` como uma rede privada, pode ser necessário liberar **Private Network Access**
na primeira chamada.

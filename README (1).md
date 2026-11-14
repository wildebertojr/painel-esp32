# Estação Meteorológica Inteligente

Painel web para acompanhar os dados enviados pela ESP32 ao ThingSpeak.

## Sensores

- DHT22: temperatura e umidade relativa do ar.
- BMP280: pressão atmosférica via I2C.
- LDR: luminosidade em escala relativa de 0 a 1000.
- MQ-135: índice relativo de gases de 0 a 100 (não é medição calibrada em ppm).

## Estrutura

- `index.html`: painel web.
- `firmware/main.py`: firmware MicroPython da ESP32.
- `firmware/config.example.py`: modelo local para as credenciais.

## Publicar o painel no GitHub Pages

1. Envie `index.html` para a raiz do repositório.
2. No GitHub, abra **Settings > Pages**.
3. Em **Build and deployment**, escolha **Deploy from a branch**.
4. Selecione a branch `main` e a pasta `/ (root)`, depois salve.

O painel consulta o canal público do ThingSpeak configurado no código HTML.

## Configurar a ESP32 no Thonny

1. Abra `firmware/main.py` no Thonny.
2. Crie no dispositivo um arquivo chamado `config.py`, usando `config.example.py` como modelo.
3. Preencha SSID, senha do Wi-Fi e Write API Key localmente.
4. Envie `main.py` e `config.py` para a ESP32.
5. Execute o `main.py`.

**Importante:** nunca publique `config.py` nem compartilhe senhas ou chaves de API. O arquivo de exemplo não contém credenciais reais.

## Observações

- O envio para o ThingSpeak ocorre a cada 20 segundos.
- O MQ-135 aguarda aproximadamente 180 segundos de aquecimento.
- Os valores de luminosidade e gases são índices relativos.
- O painel mostra as últimas 12 leituras recebidas durante a sessão.

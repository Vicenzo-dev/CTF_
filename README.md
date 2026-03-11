# 📊 Central de Controle Full-Stack (Contuflex)

> Solução inteligente para monitoramento de dados em tempo real, integrada ao ERP TOTVS.

## 📝 Sobre o Projeto
Este projeto foi desenvolvido de forma independente para a **Contuflex**, com o objetivo de otimizar a gestão de indicadores e alertas. A aplicação atua como uma camada de inteligência sobre o **ERP TOTVS**, extraindo dados diretamente do banco SQL para oferecer uma visão clara e imediata da operação.

Com esta implementação, conseguimos um controle muito mais preciso: tudo o que é atualizado no sistema oficial reflete instantaneamente no painel, eliminando processos manuais e atrasos na informação.

## ✨ Diferenciais e Impacto
* **Integração TOTVS:** Extração automatizada de dados via SQL para monitoramento fiel ao sistema.
* **Sincronização em Tempo Real:** Atualização dinâmica de alertas e métricas baseada na movimentação do ERP.
* **Controle Operacional:** Painel focado em identificar pendências (count-alerta) e exibir dados filtrados para tomada de decisão rápida.

## 🛠️ Tecnologias Utilizadas
* **Back-end:** Python + Flask (API e Regras de Negócio).
* **Banco de Dados:** SQL Server (Conexão via **pyodbc** extraindo dados do Protheus/TOTVS).
* **Front-end:** HTML5, CSS3 e JavaScript Vanilla (Interface reativa e manipulação do DOM).
* **Automação:** Scripts de inicialização em lote (`.bat`) para facilitar o uso no dia a dia da firma.

## 🚀 Como Executar
1. Certifique-se de ter o **Python 3.x** e o driver do **SQL Server** instalados.
2. Configure as credenciais de acesso ao banco do sistema no arquivo `app.py`.
3. Instale as dependências:
   ```bash
   pip install flask pyodbc

4. Configure a sua string de conexão no arquivo app.py.
5. Execute o sistema através do arquivo Iniciar_Sistema.bat ou via terminal:
    ```bash
    python app.py

Desenvolvido por Vicenzo Henrique Da Silva Conceição!


    

   

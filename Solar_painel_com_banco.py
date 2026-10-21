import tkinter as tk
from tkinter import scrolledtext
import threading
import sqlite3
import os
from groq import Groq

# Coloque sua chave da API aqui
client = Groq(api_key='')

# --- CONFIGURAÇÃO DO BANCO DE DADOS SQLite ---
CAMINHO_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chat_memoria.db")

def inicializar_banco():
    conexao = sqlite3.connect(CAMINHO_DB)
    cursor = conexao.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mensagens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            papel TEXT NOT NULL,
            conteudo TEXT NOT NULL
        )
    """)
    conexao.commit()
    conexao.close()
    print(f"Banco de dados pronto em: {CAMINHO_DB}")

def salvar_mensagem_db(papel, conteudo):
    conexao = sqlite3.connect(CAMINHO_DB)
    cursor = conexao.cursor()
    cursor.execute("INSERT INTO mensagens (papel, conteudo) VALUES (?, ?)", (papel, conteudo))
    conexao.commit()
    conexao.close()
    print(f"[SQLite] Salvo [{papel}]: {conteudo[:30]}...")

def carregar_historico_db(limite=10):
    conexao = sqlite3.connect(CAMINHO_DB)
    cursor = conexao.cursor()
    cursor.execute("SELECT papel, conteudo FROM mensagens ORDER BY id DESC LIMIT ?", (limite,))
    resultados = cursor.fetchall()
    conexao.close()
    
    resultados.reverse()
    historico = [{'role': papel, 'content': conteudo} for papel, conteudo in resultados]
    return historico

# Inicializa o banco ao abrir o script
inicializar_banco()

# Prompt ajustado com preços realistas e travas de segurança rigorosas
SYSTEM_PROMPT = '''
# CONTEXTO E MISSÃO
Você é o principal vendedor e especialista da "X Solar Limpezas", uma empresa referência em Guarulhos-SP.
Sua ÚNICA missão é conversar de forma natural, humanizada e fechar vendas de limpeza e manutenção de painéis solares.

# REGRA DE OURO DA CONVERSA (MUITO IMPORTANTE)
- UMA ETAPA POR VEZ: Nunca envie blocos gigantes de texto. Nunca mande a tabela de preços completa. Faça UMA pergunta e aguarde a resposta do cliente.
- SEJA NATURAL: Fale como um humano no WhatsApp. Sem excesso de negritos, sem listas longas. 
- SÓ PASSE O TELEFONE NO FINAL: Nunca entregue o número de telefone no começo. O telefone (11) xxxxx-xxxx só deve ser enviado quando o cliente disser "quero contratar", "vamos agendar" ou "como eu pago?".

# PRECIFICAÇÃO (Apenas para o seu conhecimento, não jogue isso tudo no cliente)
- Limpeza Residencial: R$ 35,00 por painel. ATENÇÃO: Se der menos de R$ 150,00, cobre a taxa mínima de visita de R$ 150,00.
- Limpeza Comercial/Empresarial: R$ 25,00 por painel.
- Contrato preventivo: 30% de desconto.

# FLUXO DE VENDAS (Siga passo a passo, trocando mensagens com o cliente)
PASSO 1: Cumprimente de forma educada e pergunte se é residência ou empresa e quantas placas são. PARE E ESPERE A RESPOSTA.
PASSO 2: Com a resposta do cliente, calcule mentalmente. Dê apenas o valor que serve para ele. Comente rapidamente que placa suja perde até 30% da geração de energia, então a limpeza se paga sozinha na economia da conta de luz. PARE E ESPERE O CLIENTE CONCORDAR.
PASSO 3: Pergunte se podemos agendar a limpeza.
PASSO 4: Se ele topar, aí sim você passa o telefone.

# LIMITES ESTRITOS
- PROIBIDO ENSINAR A LIMPAR: Se perguntarem como limpar em casa, alerte sobre o risco de choque elétrico, quebra do vidro e perda da garantia da placa. Ofereça nosso serviço.
- SÓ FALE DE ENERGIA SOLAR: Se o assunto fugir, corte educadamente e volte para as placas solares.
'''

def enviar_mensagem(event=None):
    mensagem_usuario = entrada_texto.get()
    if not mensagem_usuario.strip():
        return
    
    area_chat.config(state=tk.NORMAL)
    area_chat.insert(tk.END, f"Cliente: {mensagem_usuario}\n\n", "user")
    area_chat.config(state=tk.DISABLED)
    area_chat.yview(tk.END)
    entrada_texto.delete(0, tk.END)

    # Salva no banco SQLite
    salvar_mensagem_db('user', mensagem_usuario)

    area_chat.config(state=tk.NORMAL)
    area_chat.insert(tk.END, "Vendedor digitando...\n", "temp")
    area_chat.config(state=tk.DISABLED)
    area_chat.yview(tk.END)

    threading.Thread(target=obter_resposta_groq).start()

def obter_resposta_groq():
    try:
        historico_recente = carregar_historico_db(limite=10)
        mensagens_para_ia = [{'role': 'system', 'content': SYSTEM_PROMPT}] + historico_recente

        resposta = client.chat.completions.create(
            model='openai/gpt-oss-120b', 
            messages=mensagens_para_ia,
            temperature=0.6,
        )
        
        texto_resposta = resposta.choices[0].message.content
        
        # Salva a resposta da IA no banco SQLite
        salvar_mensagem_db('assistant', texto_resposta)
        
        janela.after(0, atualizar_interface, texto_resposta)
        
    except Exception as e:
        janela.after(0, atualizar_interface, f"Erro: {str(e)}")

def atualizar_interface(texto):
    area_chat.config(state=tk.NORMAL)
    
    pos_fim = area_chat.index("end-1c")
    pos_inicio = area_chat.search("Vendedor digitando...", "1.0", stopindex=pos_fim)
    if pos_inicio:
        area_chat.delete(pos_inicio, f"{pos_inicio} lineend + 1 chars")
        
    area_chat.insert(tk.END, f"X Solar: {texto}\n\n", "bot")
    area_chat.config(state=tk.DISABLED)
    area_chat.yview(tk.END)

# --- INTERFACE GRÁFICA ---
janela = tk.Tk()
janela.title("X Solar Limpezas - Atendimento Comercial com SQLite")
janela.geometry("650x750")
janela.configure(bg="#1e272e")

frame_chat = tk.Frame(janela, bg="#1e272e")
frame_chat.pack(padx=20, pady=20, fill=tk.BOTH, expand=True)

area_chat = scrolledtext.ScrolledText(frame_chat, wrap=tk.WORD, font=("Arial", 12), bg="#f1f2f6", fg="#2f3542")
area_chat.pack(fill=tk.BOTH, expand=True)
area_chat.config(state=tk.DISABLED)

area_chat.tag_config("user", foreground="#3742fa", font=("Arial", 12, "bold"))
area_chat.tag_config("bot", foreground="#2ed573", font=("Arial", 12, "bold"))
area_chat.tag_config("temp", foreground="#a4b0be", font=("Arial", 11, "italic"))

frame_inferior = tk.Frame(janela, bg="#1e272e")
frame_inferior.pack(padx=20, pady=(0, 20), fill=tk.X)

entrada_texto = tk.Entry(frame_inferior, font=("Arial", 13), bg="#ffffff")
entrada_texto.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 15), ipady=12)
entrada_texto.bind("<Return>", enviar_mensagem)

botao_enviar = tk.Button(frame_inferior, text="Enviar", font=("Arial", 12, "bold"), 
                         bg="#ffa502", fg="white", activebackground="#ff7f50", 
                         activeforeground="white", relief=tk.FLAT, command=enviar_mensagem)
botao_enviar.pack(side=tk.RIGHT, ipadx=20, ipady=8)

area_chat.config(state=tk.NORMAL)
area_chat.insert(tk.END, "SISTEMA: Banco de dados SQLite ativo com log no terminal.\n\n", "temp")
area_chat.config(state=tk.DISABLED)

janela.mainloop()
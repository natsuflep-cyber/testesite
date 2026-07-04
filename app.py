from flask import Flask, render_template_string, request
import numpy as np
from scipy.stats import poisson
import requests

app = Flask(__name__)

# 🔑 ESCREVA SUA CHAVE DA API-FOOTBALL ENTRE AS ASPAS ABAIXO:
API_KEY = "SUA_CHAVE_AQUI"

def buscar_dados_reais(nome_time):
    """
    Conecta com a API real de futebol, valida se o time existe
    e calcula a média real de gols feitos e sofridos.
    """
    headers = {
        'x-rapidapi-host': "v3.football.api-sports.io",
        'x-rapidapi-key': API_KEY
    }
    
    # 1. Busca o ID oficial do time na API para evitar erros de digitação
    url_time = f"https://v3.football.api-sports.io/teams?search={nome_time}"
    try:
        res_time = requests.get(url_time, headers=headers, timeout=10).json()
        if not res_time.get('response'):
            return None, None # Time não existe de verdade
        
        id_time = res_time['response'][0]['team']['id']
        
        # 2. Busca o histórico de gols desse time (usamos uma liga padrão ou geral)
        # Para o teste, pegamos estatísticas gerais recentes da temporada de 2026
        url_stats = f"https://v3.football.api-sports.io/teams/statistics?season=2026&team={id_time}&league=1" # 1 = Copa do Mundo / Geral
        res_stats = requests.get(url_stats, headers=headers, timeout=10).json()
        
        # Coleta as médias reais do banco de dados
        gols_feitos = res_stats['response']['goals']['for']['average']['total']
        gols_sofridos = res_stats['response']['against']['average']['total']
        
        # Converte para float (ex: "1.5" vira 1.5). Se não achar, define uma média padrão
        atq = float(gols_feitos) if gols_feitos else 1.2
        df = float(gols_sofridos) if gols_sofridos else 1.1
        
        return atq, df
    except Exception:
        return None, None

def calcular_probabilidades_placar(nome_casa, nome_fora):
    at_casa, df_casa = buscar_dados_reais(nome_casa)
    at_fora, df_fora = buscar_dados_reais(nome_fora)
    
    # Validação rigorosa: se o time não existe no mundo real, para aqui
    if at_casa is None or at_fora is None:
        return {"erro": "Um ou ambos os times informados não foram encontrados na base de dados real! Verifique a grafia."}
    
    media_gols = 1.35
    lambda_casa = at_casa * df_fora * media_gols
    lambda_fora = at_fora * df_casa * media_gols
    
    max_gols = 6
    matriz_placar = np.zeros((max_gols, max_gols))
    
    for g_casa in range(max_gols):
        for g_fora in range(max_gols):
            matriz_placar[g_casa, g_fora] = poisson.pmf(g_casa, lambda_casa) * poisson.pmf(g_fora, lambda_fora)
            
    g_casa_prev, g_fora_prev = np.unravel_index(matriz_placar.argmax(), matriz_placar.shape)
    
    prob_vitoria_casa = np.sum(np.tril(matriz_placar, -1)) * 100
    prob_empate = np.sum(np.diag(matriz_placar)) * 100
    prob_vitoria_fora = np.sum(np.triu(matriz_placar, 1)) * 100
    
    return {
        "placar": f"{g_casa_prev} x {g_fora_prev}",
        "confianca": round(matriz_placar[g_casa_prev, g_fora_prev] * 100, 1),
        "p_casa": round(prob_vitoria_casa, 1),
        "p_empate": round(prob_empate, 1),
        "p_fora": round(prob_vitoria_fora, 1),
        "at_casa": at_casa, "df_casa": df_casa,
        "at_fora": at_fora, "df_fora": df_fora
    }

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IA Preditora Real-Time</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 500px; margin: 40px auto; padding: 20px; background: #0f172a; color: #f8fafc; }
        .card { background: #1e293b; padding: 30px; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.4); border: 1px solid #334155; }
        h2 { text-align: center; color: #38bdf8; margin-top: 0; font-size: 24px; }
        p.subtitle { text-align: center; color: #94a3b8; font-size: 14px; margin-top: -15px; margin-bottom: 25px; }
        input { width: 100%; padding: 12px; margin-bottom: 15px; border: 1px solid #475569; border-radius: 8px; background: #0f172a; color: white; box-sizing: border-box; font-size: 16px; }
        button { background: #0284c7; color: white; border: none; padding: 14px; border-radius: 8px; cursor: pointer; width: 100%; font-size: 16px; font-weight: bold; }
        .resultado { margin-top: 25px; padding: 20px; background: #0c4a6e; border: 1px solid #0284c7; border-radius: 12px; text-align: center; }
        .erro { margin-top: 25px; padding: 15px; background: #7f1d1d; border: 1px solid #ef4444; border-radius: 12px; text-align: center; color: #fca5a5; }
        .placar-box { font-size: 42px; font-weight: bold; color: #38bdf8; margin: 15px 0; letter-spacing: 3px; }
        ul { list-style: none; padding: 0; text-align: left; max-width: 280px; margin: 15px auto 0 auto; }
        li { padding: 8px 0; border-bottom: 1px solid #0369a1; font-size: 15px; display: flex; justify-content: space-between; }
    </style>
</head>
<body>
    <div class="card">
        <h2>🌐 IA Preditora Profissional</h2>
        <p class="subtitle">Conectada à API Oficial de Futebol (Dados 2026)</p>
        <form method="POST">
            <input type="text" name="casa" placeholder="Time da Casa (Ex: Brasil)" value="{{ casa if casa else '' }}" required>
            <input type="text" name="fora" placeholder="Time de Fora (Ex: Noruega)" value="{{ fora if fora else '' }}" required>
            <button type="submit">Analisar Dados Reais</button>
        </form>

        {% if res %}
            {% if res.erro %}
                <div class="erro">
                    ⚠️ {{ res.erro }}
                </div>
            {% else %}
                <div class="resultado">
                    <h3 style="margin:0; color:#bae6fd;">Palpite para {{ casa }} x {{ fora }}:</h3>
                    <div class="placar-box">{{ res.placar }}</div>
                    <p style="font-size: 13px; margin: 0 0 15px 0; color: #93c5fd;">Confiança Estatística: {{ res.confianca }}%</p>
                    <div style="font-size: 11px; color: #94a3b8; margin-bottom: 10px;">
                        Média real da API: {{ casa }} ({{ res.at_casa }} Gols/j) | {{ fora }} ({{ res.at_fora }} Gols/j)
                    </div>
                    <ul>
                        <li><span>🟢 Vitória {{ casa }}:</span> <strong>{{ res.p_casa }}%</strong></li>
                        <li><span>⚪ Empate:</span> <strong>{{ res.p_empate }}%</strong></li>
                        <li><span>🔴 Vitória {{ fora }}:</span> <strong>{{ res.p_fora }}%</strong></li>
                    </ul>
                </div>
            {% endif %}
        {% endif %}
    </div>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        casa = request.form["casa"]
        fora = request.form["fora"]
        res = calcular_probabilidades_placar(casa, fora)
        return render_template_string(HTML_TEMPLATE, casa=casa, fora=fora, res=res)
    return render_template_string(HTML_TEMPLATE)

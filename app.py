from flask import Flask, render_template_string, request
import numpy as np
from scipy.stats import poisson
import requests
from datetime import datetime

app = Flask(__name__)

# 🔑 Sua chave ativa da API-Football
API_KEY = "3afab3b2657ded0519feb1cbb7dc606a"

def buscar_dados_e_palpite(nome_casa, nome_fora):
    headers = {
        'x-rapidapi-host': "v3.football.api-sports.io",
        'x-rapidapi-key': API_KEY
    }
    
    traducao = {
        "brasil": "brazil", "noruega": "norway", "espanha": "spain",
        "alemanha": "germany", "inglaterra": "england", "itália": "italy",
        "italia": "italy", "frança": "france", "franca": "france",
        "argentina": "argentina", "portugal": "portugal"
    }
    
    casa_busca = traducao.get(nome_casa.lower().strip(), nome_casa.lower().strip())
    fora_busca = traducao.get(nome_fora.lower().strip(), nome_fora.lower().strip())
    
    try:
        # 1. Buscar os IDs dos dois times na API para validar se existem no mundo real
        res_casa = requests.get(f"https://v3.football.api-sports.io/teams?search={casa_busca}", headers=headers, timeout=10).json()
        res_fora = requests.get(f"https://v3.football.api-sports.io/teams?search={fora_busca}", headers=headers, timeout=10).json()
        
        if not res_casa.get('response') or not res_fora.get('response'):
            return {"erro": "Um ou ambos os times não foram encontrados na base de dados real! Verifique a grafia."}
            
        id_casa = res_casa['response'][0]['team']['id']
        id_fora = res_fora['response'][0]['team']['id']
        
        # Valores padrão de gols (caso não ache histórico recente)
        at_casa, df_casa, at_fora, df_fora = 1.6, 1.1, 1.4, 1.2
        tipo_jogo = "Simulação de Amistoso"
        info_extra = "Não há partidas oficiais agendadas para os próximos dias."
        
        # 2. Verificar se existe um próximo jogo agendado na agenda oficial
        url_fixtures = f"https://v3.football.api-sports.io/fixtures?team={id_casa}&next=10"
        res_fixtures = requests.get(url_fixtures, headers=headers, timeout=10).json()
        
        jogo_real = None
        if res_fixtures.get('response'):
            for f in res_fixtures['response']:
                if f['teams']['away']['id'] == id_fora or f['teams']['home']['id'] == id_fora:
                    jogo_real = f
                    break
                    
        # 3. Se o jogo for real, puxa dados específicos do campeonato real
        if jogo_real:
            league_id = jogo_real['league']['id']
            season = jogo_real['league']['season']
            data_jogo = datetime.strptime(jogo_real['fixture']['date'][:10], "%Y-%m-%d").strftime("%d/%m/%Y")
            tipo_jogo = f"Jogo Real Confirmado: {jogo_real['league']['name']}"
            info_extra = f"Partida agendada para o dia {data_jogo}."
            
            url_stats_casa = f"https://v3.football.api-sports.io/teams/statistics?season={season}&team={id_casa}&league={league_id}"
            url_stats_fora = f"https://v3.football.api-sports.io/teams/statistics?season={season}&team={id_fora}&league={league_id}"
            
            res_stats_casa = requests.get(url_stats_casa, headers=headers, timeout=10).json()
            res_stats_fora = requests.get(url_stats_fora, headers=headers, timeout=10).json()
            
            try:
                if res_stats_casa.get('response') and res_stats_casa['response']['goals']['for']['average']['total']:
                    at_casa = float(res_stats_casa['response']['goals']['for']['average']['total'])
                    df_casa = float(res_stats_casa['response']['goals']['against']['average']['total'])
                if res_stats_fora.get('response') and res_stats_fora['response']['goals']['for']['average']['total']:
                    at_fora = float(res_stats_fora['response']['goals']['for']['average']['total'])
                    df_fora = float(res_stats_fora['response']['goals']['against']['average']['total'])
            except Exception:
                pass
                
        # 4. Executa o cálculo estatístico de Poisson
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
            "tipo": tipo_jogo,
            "info": info_extra,
            "real": True if jogo_real else False
        }
    except Exception:
        return {"erro": "Erro ao conectar com o banco de dados de futebol. Tente novamente."}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IA Preditora Inteligente</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 500px; margin: 40px auto; padding: 20px; background: #0f172a; color: #f8fafc; }
        .card { background: #1e293b; padding: 30px; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.4); border: 1px solid #334155; }
        h2 { text-align: center; color: #38bdf8; margin-top: 0; font-size: 24px; }
        p.subtitle { text-align: center; color: #94a3b8; font-size: 14px; margin-top: -15px; margin-bottom: 25px; }
        input { width: 100%; padding: 12px; margin-bottom: 15px; border: 1px solid #475569; border-radius: 8px; background: #0f172a; color: white; box-sizing: border-box; font-size: 16px; }
        button { background: #0284c7; color: white; border: none; padding: 14px; border-radius: 8px; cursor: pointer; width: 100%; font-size: 16px; font-weight: bold; width: 100%; }
        .resultado { margin-top: 25px; padding: 20px; border-radius: 12px; text-align: center; }
        .modo-real { background: #0c4a6e; border: 1px solid #0284c7; }
        .modo-simulado { background: #1e1b4b; border: 1px solid #6366f1; }
        .erro { margin-top: 25px; padding: 15px; background: #7f1d1d; border: 1px solid #ef4444; border-radius: 12px; text-align: center; color: #fca5a5; }
        .placar-box { font-size: 42px; font-weight: bold; margin: 15px 0; letter-spacing: 3px; }
        .color-real { color: #38bdf8; }
        .color-simulado { color: #818cf8; }
        .badge { padding: 4px 10px; border-radius: 12px; font-size: 11px; display: inline-block; margin-bottom: 10px; font-weight: bold; }
        .badge-real { background: #0284c7; color: white; }
        .badge-simulado { background: #4f46e5; color: white; }
        ul { list-style: none; padding: 0; text-align: left; max-width: 280px; margin: 15px auto 0 auto; }
        li { padding: 8px 0; border-bottom: 1px solid #334155; font-size: 15px; display: flex; justify-content: space-between; }
    </style>
</head>
<body>
    <div class="card">
        <h2>🤖 IA Preditora Avançada</h2>
        <p class="subtitle">Análise de Jogos Reais + Modo Simulação Ativo</p>
        <form method="POST">
            <input type="text" name="casa" placeholder="Time da Casa (Ex: Brasil)" value="{{ casa if casa else '' }}" required>
            <input type="text" name="fora" placeholder="Time de Fora (Ex: Noruega)" value="{{ fora if fora else '' }}" required>
            <button type="submit">Gerar Palpite Inteligente</button>
        </form>

        {% if res %}
            {% if res.erro %}
                <div class="erro">⚠️ {{ res.erro }}</div>
            {% else %}
                <div class="resultado {{ 'modo-real' if res.real else 'modo-simulado' }}">
                    <div class="badge {{ 'badge-real' if res.real else 'badge-simulado' }}">{{ res.tipo }}</div>
                    <p style="margin:5px 0; font-size:12px; color:#94a3b8;">{{ res.info }}</p>
                    <h3 style="margin:10px 0 0 0; color:#f8fafc;">{{ casa }} x {{ fora }}</h3>
                    <div class="placar-box {{ 'color-real' if res.real else 'color-simulado' }}">{{ res.placar }}</div>
                    <p style="font-size: 13px; margin: 0 0 15px 0; color: #cbd5e1;">Confiança Estatística: {{ res.confianca }}%</p>
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
        res = buscar_dados_e_palpite(casa, fora)
        return render_template_string(HTML_TEMPLATE, casa=casa, fora=fora, res=res)
    return render_template_string(HTML_TEMPLATE)

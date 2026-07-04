from flask import Flask, render_template_string, request
import numpy as np
from scipy.stats import poisson
import requests
from datetime import datetime, timedelta

app = Flask(__name__)

# 🔑 Sua chave ativa da API-Football
API_KEY = "3afab3b2657ded0519feb1cbb7dc606a"

def buscar_dados_reais_e_calcular(nome_casa, nome_fora):
    headers = {
        'x-rapidapi-host': "v3.football.api-sports.io",
        'x-rapidapi-key': API_KEY
    }
    
    # Dicionário expandido para ajudar na busca de times comuns em português
    traducao = {
        "brasil": "brazil", "noruega": "norway", "espanha": "spain",
        "alemanha": "germany", "inglaterra": "england", "itália": "italy",
        "italia": "italy", "frança": "france", "franca": "france",
        "argentina": "argentina", "portugal": "portugal",
        "flamengo": "flamengo", "palmeiras": "palmeiras", "são paulo": "sao paulo",
        "corinthians": "corinthians", "real madrid": "real madrid", "barcelona": "barcelona"
    }
    
    casa_busca = traducao.get(nome_casa.lower().strip(), nome_casa.lower().strip())
    fora_busca = traducao.get(nome_fora.lower().strip(), nome_fora.lower().strip())
    
    try:
        hoje = datetime.now().strftime("%Y-%m-%d")
        amanha = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        jogo_real = None
        
        # Varre estritamente a lista de jogos globais de hoje e amanhã
        for data_analise in [hoje, amanha]:
            url_fixtures = f"https://v3.football.api-sports.io/fixtures?date={data_analise}"
            res_fixtures = requests.get(url_fixtures, headers=headers, timeout=10).json()
            
            if res_fixtures.get('response'):
                for f in res_fixtures['response']:
                    h_name = f['teams']['home']['name'].lower()
                    a_name = f['teams']['away']['name'].lower()
                    
                    if (casa_busca in h_name and fora_busca in a_name) or (fora_busca in h_name and casa_busca in a_name):
                        jogo_real = f
                        break
            if jogo_real:
                break

        # CRÍTICO: Se não achou na grade real de hoje/amanhã, não inventa palpite!
        if not jogo_real:
            return {"erro": f"Nenhum jogo oficial agendado para Hoje ou Amanhã entre '{nome_casa}' e '{nome_fora}' no banco de dados da API. Verifique se os nomes correspondem à grafia internacional."}
            
        id_casa = jogo_real['teams']['home']['id']
        id_fora = jogo_real['teams']['away']['id']
        league_id = jogo_real['league']['id']
        season = jogo_real['league']['season']
        data_jogo = datetime.strptime(jogo_real['fixture']['date'][:10], "%Y-%m-%d").strftime("%d/%m/%Y")
        
        # Busca estatísticas reais de desempenho estritamente dentro deste campeonato
        url_stats_casa = f"https://v3.football.api-sports.io/teams/statistics?season={season}&team={id_casa}&league={league_id}"
        url_stats_fora = f"https://v3.football.api-sports.io/teams/statistics?season={season}&team={id_fora}&league={league_id}"
        
        res_stats_casa = requests.get(url_stats_casa, headers=headers, timeout=10).json()
        res_stats_fora = requests.get(url_stats_fora, headers=headers, timeout=10).json()
        
        # Tenta extrair as médias reais matemáticas de gols
        try:
            gols_f_casa = res_stats_casa['response']['goals']['for']['average']['total']
            gols_s_casa = res_stats_casa['response']['against']['average']['total']
            gols_f_fora = res_stats_fora['response']['goals']['for']['average']['total']
            gols_s_fora = res_stats_fora['response']['against']['average']['total']
            
            if not all([gols_f_casa, gols_s_casa, gols_f_fora, gols_s_fora]):
                return {"erro": "Jogo encontrado, mas a API ainda não possui estatísticas de gols suficientes nesta temporada para calcular o palpite."}
                
            at_casa, df_casa = float(gols_f_casa), float(gols_s_casa)
            at_fora, df_fora = float(gols_f_fora), float(gols_s_fora)
        except Exception:
            return {"erro": "Erro ao ler as estatísticas de desempenho dos times na API para este campeonato."}
            
        # Distribuição de Poisson pura baseada nos dados extraídos
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
            "campeonato": jogo_real['league']['name'],
            "data": data_jogo
        }
    except Exception as e:
        return {"erro": "Falha de comunicação com o servidor de dados do futebol."}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IA Analisadora Real</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; max-width: 500px; margin: 40px auto; padding: 20px; background: #0f172a; color: #f8fafc; }
        .card { background: #1e293b; padding: 30px; border-radius: 16px; border: 1px solid #334155; }
        h2 { text-align: center; color: #38bdf8; margin: 0 0 20px 0; }
        input { width: 100%; padding: 12px; margin-bottom: 15px; border: 1px solid #475569; border-radius: 8px; background: #0f172a; color: white; box-sizing: border-box; }
        button { background: #0284c7; color: white; border: none; padding: 14px; border-radius: 8px; cursor: pointer; width: 100%; font-weight: bold; }
        .resultado { margin-top: 25px; padding: 20px; background: #0c4a6e; border: 1px solid #0284c7; border-radius: 12px; text-align: center; }
        .erro { margin-top: 25px; padding: 15px; background: #7f1d1d; border: 1px solid #ef4444; border-radius: 12px; text-align: center; color: #fca5a5; font-size: 14px; }
        .placar-box { font-size: 44px; font-weight: bold; color: #38bdf8; margin: 15px 0; }
        ul { list-style: none; padding: 0; text-align: left; max-width: 280px; margin: 15px auto 0 auto; }
        li { padding: 8px 0; border-bottom: 1px solid #0369a1; font-size: 15px; display: flex; justify-content: space-between; }
    </style>
</head>
<body>
    <div class="card">
        <h2>📊 IA de Dados Reais</h2>
        <form method="POST">
            <input type="text" name="casa" placeholder="Time da Casa (Ex: Real Madrid)" value="{{ casa if casa else '' }}" required>
            <input type="text" name="fora" placeholder="Time de Fora (Ex: Barcelona)" value="{{ fora if fora else '' }}" required>
            <button type="submit">Analisar Partida Real</button>
        </form>

        {% if res %}
            {% if res.erro %}
                <div class="erro">⚠️ {{ res.erro }}</div>
            {% else %}
                <div class="resultado">
                    <div style="background:#0284c7; color:white; padding:3px 8px; border-radius:8px; font-size:11px; display:inline-block;">{{ res.campeonato }} - {{ res.data }}</div>
                    <h3 style="margin:10px 0 0 0;">{{ casa }} x {{ fora }}</h3>
                    <div class="placar-box">{{ res.placar }}</div>
                    <p style="font-size: 13px; color: #93c5fd; margin: 0 0 10px 0;">Confiança Estatística: {{ res.confianca }}%</p>
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
        res = buscar_dados_reais_e_calcular(casa, fora)
        return render_template_string(HTML_TEMPLATE, casa=casa, fora=fora, res=res)
    return render_template_string(HTML_TEMPLATE)

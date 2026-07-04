from flask import Flask, render_template_string, request
import numpy as np
from scipy.stats import poisson

app = Flask(__name__)

def calcular_probabilidades_placar(at_casa, df_casa, at_fora, df_fora):
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
        "p_fora": round(prob_vitoria_fora, 1)
    }

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IA Preditora de Futebol</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 600px; margin: 40px auto; padding: 20px; line-height: 1.6; background: #0f172a; color: #f8fafc; }
        .card { background: #1e293b; padding: 30px; border-radius: 12px; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.3); border: 1px solid #334155; }
        h2 { text-align: center; color: #38bdf8; margin-bottom: 25px; }
        .time-section { background: #111827; padding: 15px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #1f2937; }
        h4 { margin: 0 0 10px 0; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; }
        label { display: block; margin-bottom: 5px; font-size: 14px; color: #cbd5e1; }
        input { width: 100%; padding: 10px; margin-bottom: 12px; border: 1px solid #475569; border-radius: 6px; background: #0f172a; color: white; box-sizing: border-box; }
        input:focus { border-color: #38bdf8; outline: none; }
        button { background: #0284c7; color: white; border: none; padding: 12px; border-radius: 6px; cursor: pointer; width: 100%; font-size: 16px; font-weight: bold; transition: background 0.2s; }
        button:hover { background: #0369a1; }
        .resultado { margin-top: 25px; padding: 20px; background: #0c4a6e; border: 1px solid #0284c7; border-radius: 8px; text-align: center; }
        .placar-box { font-size: 32px; font-weight: bold; color: #38bdf8; margin: 15px 0; letter-spacing: 2px; }
        ul { list-style: none; padding: 0; text-align: left; max-width: 250px; margin: 15px auto 0 auto; }
        li { padding: 6px 0; border-bottom: 1px solid #0369a1; font-size: 15px; }
        li:last-child { border: none; }
    </style>
</head>
<body>
    <div class="card">
        <h2>🤖 IA Preditora de Placares</h2>
        <form method="POST">
            <div class="time-section">
                <h4>Mandante / Casa</h4>
                <label>Nome do Time:</label>
                <input type="text" name="casa" placeholder="Ex: Brasil" value="{{ casa if casa else '' }}" required>
                <label>Força de Ataque (Média de gols feitos):</label>
                <input type="number" step="0.01" name="at_casa" placeholder="Ex: 1.65" value="{{ request.form.at_casa if request.method == 'POST' else '' }}" required>
                <label>Força de Defesa (Média de gols sofridos):</label>
                <input type="number" step="0.01" name="df_casa" placeholder="Ex: 0.80" value="{{ request.form.df_casa if request.method == 'POST' else '' }}" required>
            </div>
            
            <div class="time-section">
                <h4>Visitante / Fora</h4>
                <label>Nome do Time:</label>
                <input type="text" name="fora" placeholder="Ex: Noruega" value="{{ fora if fora else '' }}" required>
                <label>Força de Ataque (Média de gols feitos):</label>
                <input type="number" step="0.01" name="at_fora" placeholder="Ex: 1.20" value="{{ request.form.at_fora if request.method == 'POST' else '' }}" required>
                <label>Força de Defesa (Média de gols sofridos):</label>
                <input type="number" step="0.01" name="df_fora" placeholder="Ex: 1.30" value="{{ request.form.df_fora if request.method == 'POST' else '' }}" required>
            </div>
            
            <button type="submit">Gerar Análise Computacional</button>
        </form>

        {% if res %}
        <div class="resultado">
            <h3>Resultado da Simulação:</h3>
            <p style="margin:0; color:#bae6fd;">{{ casa }} vs {{ fora }}</p>
            <div class="placar-box">{{ res.placar }}</div>
            <p style="font-size: 14px; margin: 0; color: #93c5fd;">Confiança do Placar Exato: {{ res.confianca }}%</p>
            
            <ul>
                <li>🟢 Vitória {{ casa }}: <strong>{{ res.p_casa }}%</strong></li>
                <li>⚪ Empate: <strong>{{ res.p_empate }}%</strong></li>
                <li>🔴 Vitória {{ fora }}: <strong>{{ res.p_fora }}%</strong></li>
            </ul>
        </div>
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
        res = calcular_probabilidades_placar(
            float(request.form["at_casa"]), float(request.form["df_casa"]),
            float(request.form["at_fora"]), float(request.form["df_fora"])
        )
        return render_template_string(HTML_TEMPLATE, casa=casa, fora=fora, res=res)
    return render_template_string(HTML_TEMPLATE)

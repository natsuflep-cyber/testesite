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

# Interface HTML simples embutida para facilitar o deploy
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>IA Preditora de Futebol</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 600px; margin: 40px auto; padding: 20px; line-height: 1.6; background: #f4f4f9; }
        .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        input { width: 100%; padding: 8px; margin: 8px 0 16px 0; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-radius; }
        button { background: #0070f3; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; width: 100%; font-size: 16px; }
        .resultado { margin-top: 20px; padding: 15px; background: #e7f5ff; border-left: 5px solid #0070f3; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="card">
        <h2>🤖 IA Preditora de Placares</h2>
        <form method="POST">
            <input type="text" name="casa" placeholder="Time da Casa (ex: Brasil)" required>
            <input type="number" step="0.1" name="at_casa" placeholder="Força de Ataque Casa (ex: 1.5)" required>
            <input type="number" step="0.1" name="df_casa" placeholder="Força de Defesa Casa (ex: 0.8)" required>
            <hr>
            <input type="text" name="fora" placeholder="Time de Fora (ex: Noruega)" required>
            <input type="number" step="0.1" name="at_fora" placeholder="Força de Ataque Fora (ex: 1.1)" required>
            <input type="number" step="0.1" name="df_fora" placeholder="Força de Defesa Fora (ex: 1.2)" required>
            <button type="submit">Calcular Palpite</button>
        </form>

        {% if res %}
        <div class="resultado">
            <h3>Palpite para {{ casa }} x {{ fora }}:</h3>
            <p><strong>🎯 Placar Sugerido: {{ res.placar }}</strong> (Confiança: {{ res.confianca }}%)</p>
            <p>📊 Probabilidades:</p>
            <ul>
                <li>Vitória {{ casa }}: {{ res.p_casa }}%</li>
                <li>Empate: {{ res.p_empate }}%</li>
                <li>Vitória {{ fora }}: {{ res.p_fora }}%</li>
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

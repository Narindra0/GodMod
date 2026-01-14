import streamlit as st
import pandas as pd
import sqlite3
import os
import time
from datetime import datetime
from src.core import config

# Configuration de la page
st.set_page_config(
    page_title="GODMOD V2 - Intelligence Center",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- STYLE PREMIUM ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&display=swap');
    
    .main { background-color: #0d1117; }
    
    .stMetric {
        background: linear-gradient(145deg, #161b22, #0d1117);
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #30363d;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    
    .big-font {
        font-family: 'Orbitron', sans-serif;
        font-size: 24px !important;
        font-weight: bold;
        color: #58a6ff;
    }
    
    div[data-testid="stExpander"] {
        border-radius: 10px;
        border: 1px solid #30363d;
    }
    
    .status-active {
        color: #238636;
        font-weight: bold;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { opacity: 0.5; }
        50% { opacity: 1; }
        100% { opacity: 0.5; }
    }
</style>
""", unsafe_allow_html=True)

# --- LOGIQUE DE DONNÉES ---
# Note: Utilisation directe de get_db_connection dans load_all_data pour meilleure gestion

@st.cache_data(ttl=5)
def load_all_data():
    from src.core.database import get_db_connection
    with get_db_connection() as conn:
        # Performance
        df_perf = pd.read_sql_query("SELECT SUM(points_gagnes) as score, COUNT(*) as total FROM predictions WHERE succes IS NOT NULL", conn)
        df_wins = pd.read_sql_query("SELECT COUNT(*) as wins FROM predictions WHERE succes = 1", conn)
        
        # Score IA global
        df_score_ia = pd.read_sql_query("SELECT score, predictions_total, predictions_reussies, pause_until FROM score_ia WHERE id = 1", conn)
        
        # Prédictions
        df_preds = pd.read_sql_query("""
            SELECT p.journee as J, e1.nom as Domicile, e2.nom as Exterieur, p.prediction as Prono, p.resultat as Reel, p.succes
            FROM predictions p
            JOIN equipes e1 ON p.equipe_dom_id = e1.id
            JOIN equipes e2 ON p.equipe_ext_id = e2.id
            ORDER BY p.id DESC LIMIT 15
        """, conn)
        
        # Résultats réels (tous les matchs pour pagination)
        df_results = pd.read_sql_query("""
            SELECT r.journee as J, e1.nom as Domicile, r.score_dom || ' - ' || r.score_ext as Score, e2.nom as Exterieur
            FROM resultats r
            JOIN equipes e1 ON r.equipe_dom_id = e1.id
            JOIN equipes e2 ON r.equipe_ext_id = e2.id
            ORDER BY r.journee DESC, r.id DESC
        """, conn)
        
        # Classement
        df_ranking = pd.read_sql_query("""
            SELECT e.nom as Equipe, c.points as Pts, c.forme as Forme
            FROM classement c
            JOIN equipes e ON c.equipe_id = e.id
            ORDER BY c.points DESC
        """, conn)
        
        # Trend
        df_trend = pd.read_sql_query("SELECT id, points_gagnes FROM predictions WHERE succes IS NOT NULL ORDER BY id", conn)
        
        # ZEUS Data (Shadow Mode)
        df_zeus = pd.read_sql_query("""
            SELECT z.journee as J, e1.nom as Domicile, e2.nom as Exterieur, z.prediction as RawPred, z.confiance, z.timestamp
            FROM zeus_predictions z
            JOIN equipes e1 ON z.equipe_dom_id = e1.id
            JOIN equipes e2 ON z.equipe_ext_id = e2.id
            ORDER BY z.id DESC LIMIT 20
        """, conn)

        return df_perf, df_wins, df_preds, df_results, df_ranking, df_trend, df_score_ia, df_zeus

# --- INTERFACE ---
st.title("⚡ GODMOD V2 | Intelligence Center")
st.markdown(f"*Dernière mise à jour : {datetime.now().strftime('%H:%M:%S')}*")

# Chargement
# Chargement
df_perf, df_wins, df_preds, df_results, df_ranking, df_trend, df_score_ia, df_zeus = load_all_data()

score_ia = df_score_ia['score'].iloc[0] if not df_score_ia.empty else 100
ia_total = df_score_ia['predictions_total'].iloc[0] if not df_score_ia.empty else 0
ia_wins = df_score_ia['predictions_reussies'].iloc[0] if not df_score_ia.empty else 0
pause_until = df_score_ia['pause_until'].iloc[0] if not df_score_ia.empty and 'pause_until' in df_score_ia.columns else 0

# ... 
score = df_perf['score'].iloc[0] if not df_perf.empty else 0
wins = df_wins['wins'].iloc[0] if not df_wins.empty else 0
total_history = df_perf['total'].iloc[0] if not df_perf.empty else 0
win_rate = (wins / total_history * 100) if total_history > 0 else 0

# Détermination de la journée actuelle
current_journee = df_results['J'].max() if not df_results.empty else 0
current_journee += 1

# Extraction de ia_reussies avant utilisation
ia_reussies = df_score_ia['predictions_reussies'].iloc[0] if not df_score_ia.empty else 0

# VÉRIFICATION PAUSE
if pause_until >= current_journee:
    st.error(f"🛑 Renforcement du programme : attendre la journée {pause_until + 1} avant le prochain pronostic fiable.")

# Metrics
m1, m2, m3, m4, m5 = st.columns(5)
with m1: st.metric("🤖 Score IA", f"{score_ia} pts")
with m2: st.metric("Score Global", f"{score} pts")
with m3: st.metric("Taux de Réussite", f"{win_rate:.1f}%")
with m4: st.metric("Total Prédictions", f"{ia_reussies}/{ia_total}")
with m5: st.metric("Victoires", wins)

st.markdown("---")

col_left, col_right = st.columns([2, 1])

with col_left:
    tab_preds, tab_zeus, tab_results = st.tabs(["🎯 Prédictions", "⚡ Module ZEUS (Shadow)", "📜 Derniers Résultats"])
    
    with tab_preds:
        # Détermination de la journée actuelle (Max des résultats + 1)
        current_journee = df_results['J'].max() if not df_results.empty else 0
        current_journee += 1
        
        if current_journee < 4:
            st.warning("Pronostic pas encore disponible : pas encore assez de données (J < 4).")
        elif current_journee < 10:
            st.markdown("## <span style='color:red'>🚩 Prise de risque (J4-J9)</span>", unsafe_allow_html=True)
            st.info("Algorithme simplifié activé. Prudence requise.")
        else:
            st.subheader("Analyses en cours")

        if not df_preds.empty:
            # Formatage pour l'affichage (Vert/Rouge)
            def format_succes(val):
                if val == 1:
                    return "✅ Succès"
                elif val == 0:
                    return "❌ Échec"
                return "⏳ En attente"
            
            df_display = df_preds.copy()
            # On applique le formatage
            df_display['succes'] = df_display['succes'].apply(format_succes)
            
            # Renommage pour l'affichage
            df_display = df_display.rename(columns={'succes': 'Statut'})
            
            st.dataframe(
                df_display, 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "Statut": st.column_config.TextColumn(
                        "Statut",
                        help="Résultat du pronostic",
                        width="medium"
                    )
                }
            )
        else:
            st.info("Aucune prédiction enregistrée.")
            
    with tab_zeus:
        st.subheader("⚡ Activité du Module Zeus (Mode Ombre)")
        st.info("Zeus observe les matchs et propose ses actions sans parier (Shadow Mode). Comparaison en cours...")
        
        if not df_zeus.empty:
            # Mapping des actions
            def map_action(x):
                if x == 0: return "1 (Domicile)"
                elif x == 1: return "N (Nul)"
                elif x == 2: return "2 (Extérieur)"
                elif x == 3: return "SKIP (Prudence)"
                return str(x)
            
            df_z_disp = df_zeus.copy()
            df_z_disp['Action'] = df_z_disp['RawPred'].apply(map_action)
            
            # Reorder
            df_z_disp = df_z_disp[['J', 'Domicile', 'Exterieur', 'Action', 'confiance', 'timestamp']]
            
            st.dataframe(
                df_z_disp,
                use_container_width=True,
                hide_index=True,
                 column_config={
                    "Action": st.column_config.TextColumn(
                        "Conseil IA",
                        width="medium"
                    ),
                    "confiance": st.column_config.ProgressColumn(
                        "Confiance (?)",
                        min_value=0, max_value=1,
                        format="%.2f"
                    )
                }
            )
        else:
            st.warning("Aucune donnée Zeus pour l'instant. Attendez le prochain cycle.")

    with tab_results:
        st.subheader("Résultats Officiels")
        if not df_results.empty:
            # Liste des journées disponibles (de la plus récente à la plus ancienne)
            journees = sorted(df_results['J'].unique().tolist(), reverse=True)
            journee_selectionnee = st.selectbox(
                "📅 Sélectionner la journée", 
                journees, 
                index=0,
                key="journee_selector"
            )
            # Filtrer les résultats pour la journée sélectionnée
            df_filtered = df_results[df_results['J'] == journee_selectionnee]
            st.dataframe(df_filtered, use_container_width=True, hide_index=True)
        else:
            st.info("Aucun résultat enregistré.")

with col_right:
    st.subheader("📊 Top Classement")
    st.dataframe(df_ranking.head(10), use_container_width=True, hide_index=True)
    
    st.subheader("📈 Courbe de Profit")
    if not df_trend.empty:
        df_trend['Cumulative'] = df_trend['points_gagnes'].cumsum()
        st.line_chart(df_trend.set_index('id')['Cumulative'], height=200)

# --- SIDEBAR ---
st.sidebar.title("🛠️ Paramètres")
st.sidebar.markdown(f"**Statut :** <span class='status-active'>LIVE MONITORING</span>", unsafe_allow_html=True)

# Section Intelligence & Sélection Unifiée
st.sidebar.markdown("---")
st.sidebar.subheader("🧠 Intelligence & Sélection")

# Récupérer l'état actuel (on se base sur USE_INTELLIGENCE_AMELIOREE comme maître)
current_intelligence_state = config.USE_INTELLIGENCE_AMELIOREE

# Toggle unique pour tout activer/désactiver
new_intelligence_state = st.sidebar.toggle(
    "Intelligence Complète",
    value=current_intelligence_state,
    help="Active simultanément le Mode Multi-Facteurs et la Phase 3 (Sélection Améliorée)"
)

# Si l'état a changé
if new_intelligence_state != current_intelligence_state:
    from src.core import utils
    # Mise à jour globale des deux flags
    if utils.update_global_intelligence_flags(new_intelligence_state):
        # Recharger les modules
        import importlib
        import sys
        if 'src.core.config' in sys.modules:
            importlib.reload(sys.modules['src.core.config'])
            # Recharger intelligence si chargé
            if 'src.analysis.intelligence' in sys.modules:
                importlib.reload(sys.modules['src.analysis.intelligence'])
        
        # Feedback utilisateur
        if new_intelligence_state:
            st.sidebar.success("✅ Mode Intelligence Complète activé !")
        else:
            st.sidebar.info("ℹ️ Retour au Mode Standard")
        
        # Rafraîchir
        time.sleep(0.5)
        st.rerun()
    else:
        st.sidebar.error("❌ Erreur de mise à jour configuration")

# Affichage du statut
if current_intelligence_state:
    st.sidebar.markdown(
        """
        <div style='background-color: rgba(35, 134, 54, 0.2); padding: 10px; border-radius: 5px; border-left: 3px solid #238636;'>
            <span style='color: #238636; font-weight: bold;'>🟢 SYSTÈME ACTIF</span>
        </div>
        """, 
        unsafe_allow_html=True
    )
else:
    st.sidebar.markdown(
        """
        <div style='background-color: rgba(248, 81, 73, 0.1); padding: 10px; border-radius: 5px; border-left: 3px solid #f85149;'>
            <span style='color: #f85149; font-weight: bold;'>🔴 MODE SIMPLE</span>
        </div>
        """, 
        unsafe_allow_html=True
    )

st.sidebar.markdown("---")
refresh = st.sidebar.slider("Rafraîchissement (sec)", 2, 30, 5)

# Auto-refresh actif par défaut
auto_refresh = st.sidebar.checkbox("Auto-refresh", value=True)
if auto_refresh:
    time.sleep(refresh)
    st.rerun()

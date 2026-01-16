import streamlit as st
import pandas as pd
import sqlite3
import os
import time
import threading
from datetime import datetime
from src.core import config, database
from src.api.api_monitor import start_monitoring

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
        
        # ZEUS Data (Active Mode) - Avec Join Résultats pour calcul succès
        df_zeus = pd.read_sql_query("""
            SELECT 
                z.journee as J, 
                e1.nom as Domicile, 
                e2.nom as Exterieur, 
                z.prediction as RawPred, 
                z.confiance, 
                z.timestamp,
                r.score_dom, 
                r.score_ext
            FROM zeus_predictions z
            JOIN equipes e1 ON z.equipe_dom_id = e1.id
            JOIN equipes e2 ON z.equipe_ext_id = e2.id
            LEFT JOIN resultats r ON z.journee = r.journee AND z.equipe_dom_id = r.equipe_dom_id
            ORDER BY z.id DESC LIMIT 1000
        """, conn)

        return df_perf, df_wins, df_preds, df_results, df_ranking, df_trend, df_score_ia, df_zeus

# --- INTERFACE ---
st.title("⚡ GODMOD V2 | Intelligence Center")
st.markdown(f"*Dernière mise à jour : {datetime.now().strftime('%H:%M:%S')}*")

# --- INITIALISATION ET BACKGROUND MONITOR ---

def run_monitor():
    """Fonction pour lancer le monitor en arrière-plan."""
    try:
        from main import callback_predictions_ia
        print("[BACKGROUND] Démarrage du monitor API...")
        start_monitoring(
            callback_on_new_journee=callback_predictions_ia,
            verbose=False
        )
    except Exception as e:
        print(f"[BACKGROUND ERROR] {e}")

# Initialisation de la BDD au démarrage (AVANT de charger les données)
if 'db_initialized' not in st.session_state:
    try:
        database.initialiser_db()
        st.session_state.db_initialized = True
        print("[INIT] Base de données initialisée.")
    except Exception as e:
        st.error(f"Erreur initialisation BDD : {e}")

# Lancement du thread monitor s'il n'existe pas encore (singleton global)
if 'monitor_thread' not in st.session_state:
    # On utilise un flag global pour éviter les doubles lancements lors des reruns
    if not any(t.name == "GODMOD_Monitor" for t in threading.enumerate()):
        thread = threading.Thread(target=run_monitor, name="GODMOD_Monitor", daemon=True)
        thread.start()
        st.session_state.monitor_thread = True
        print("[INIT] Monitor thread lancé.")

# --- CHARGEMENT DES DONNÉES ---
df_perf, df_wins, df_preds, df_results, df_ranking, df_trend, df_score_ia, df_zeus = load_all_data()

score_ia = df_score_ia['score'].iloc[0] if not df_score_ia.empty else 100
ia_total = df_score_ia['predictions_total'].iloc[0] if not df_score_ia.empty else 0
ia_wins = df_score_ia['predictions_reussies'].iloc[0] if not df_score_ia.empty else 0
pause_until = df_score_ia['pause_until'].iloc[0] if not df_score_ia.empty and 'pause_until' in df_score_ia.columns else 0

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
    tab_preds, tab_zeus, tab_results = st.tabs(["🎯 Prédictions", "⚡ SUPER-INTELLIGENCE (Zeus v2)", "📜 Derniers Résultats"])
    
    with tab_preds:
        # Détermination de la journée actuelle (Max des résultats + 1)
        current_journee = df_results['J'].max() if not df_results.empty else 0
        current_journee += 1
        
        if current_journee < 2:
            st.warning("Pronostic pas encore disponible : pas encore assez de données (J < 2).")
        elif current_journee < 10:
            st.markdown("## <span style='color:red'>🚩 Prise de risque (J2-J9)</span>", unsafe_allow_html=True)
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
        if not df_zeus.empty:
            # --- GLOBAL STATS (Avant Filtrage) ---
            # 1. Calcul du succès sur TOUT l'historique
            stats_zeus = df_zeus.copy()
            
            def check_zeus_success(row):
                if pd.isna(row['score_dom']): return None
                res_reel = 0
                if row['score_dom'] > row['score_ext']: res_reel = 0 # 1
                elif row['score_dom'] == row['score_ext']: res_reel = 1 # N
                else: res_reel = 2 # 2
                
                if row['RawPred'] == 3: return None # Skip
                return 1 if row['RawPred'] == res_reel else 0
            
            stats_zeus['ZeusSuccess'] = stats_zeus.apply(check_zeus_success, axis=1)
            
            global_wins = stats_zeus['ZeusSuccess'].sum()
            global_attempts = stats_zeus['ZeusSuccess'].count()
            global_skips = len(stats_zeus[stats_zeus['RawPred']==3])
            global_rate = (global_wins / global_attempts * 100) if global_attempts > 0 else 0
            
            # --- HEADER + CIRCULAR PROGRESS ---
            # CSS pour le cercle de progression
            st.markdown(f"""
            <style>
                .zeus-header-container {{
                    background-color: #0d1117; 
                    border: 1px solid #238636; 
                    border-radius: 10px; 
                    padding: 20px; 
                    margin-bottom: 20px; 
                    display: flex; 
                    align-items: center;
                    justify-content: space-between;
                }}
                .zeus-info {{
                    flex-grow: 1;
                }}
                .radial-progress {{
                    position: relative;
                    width: 80px;
                    height: 80px;
                    border-radius: 50%;
                    background: conic-gradient(#3fb950 {global_rate}%, #30363d 0);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin-left: 20px;
                    box-shadow: 0 0 10px rgba(63, 185, 80, 0.2);
                }}
                .radial-progress::before {{
                    content: "";
                    position: absolute;
                    width: 70px;
                    height: 70px;
                    border-radius: 50%;
                    background-color: #0d1117;
                }}
                .percentage {{
                    position: relative;
                    font-family: 'Orbitron', sans-serif;
                    font-size: 18px;
                    font-weight: bold;
                    color: #fff;
                }}
                .metric-box {{
                    background: #161b22;
                    padding: 10px;
                    border-radius: 8px;
                    text-align: center;
                    border: 1px solid #30363d;
                    min-width: 100px;
                }}
                .metric-label {{ color: #8b949e; font-size: 12px; }}
                .metric-value {{ color: #e6edf3; font-size: 18px; font-weight: bold; }}
            </style>
            
            <div class="zeus-header-container">
                <div style="font-size: 40px; margin-right: 20px;">⚡</div>
                <div class="zeus-info">
                    <h3 style="margin: 0; color: #3fb950; font-family: 'Orbitron', sans-serif;">MODÈLE ACTIF : zeus_v3</h3>
                    <div style="margin-top: 5px; color: #8b949e;">
                        Version : Profit-Driven | Entraînement : 30 000 steps
                    </div>
                    <div style="display: flex; gap: 15px; margin-top: 15px;">
                        <div class="metric-box">
                            <div class="metric-label">Essais Validés</div>
                            <div class="metric-value">{global_attempts}</div>
                        </div>
                        <div class="metric-box">
                            <div class="metric-label">Mode Prudence (SKIP)</div>
                            <div class="metric-value" style="color: #d29922;">{global_skips}</div>
                        </div>
                        <div class="metric-box">
                            <div class="metric-label">Victoires</div>
                            <div class="metric-value" style="color: #3fb950;">{int(global_wins)}</div>
                        </div>
                    </div>
                </div>
                <div class="radial-progress">
                    <span class="percentage">{global_rate:.1f}%</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # --- FILTRAGE ET TABLEAU ---
            st.markdown("### 📜 Historique des Prédictions")
            
            # Sélecteur de Journée
            journees_z = sorted(df_zeus['J'].unique().tolist(), reverse=True)
            journee_sel_z = st.selectbox("📅 Filtrer par Journée", journees_z, index=0, key="zeus_j_selector")
            
            # Filtrage pour le tableau
            df_zeus_filtered = df_zeus[df_zeus['J'] == journee_sel_z].copy()
            
            # Recalcul local pour la colonne succès dans le tableau uniquement
            df_zeus_filtered['ZeusSuccess'] = df_zeus_filtered.apply(check_zeus_success, axis=1)
            
            # Mapping des actions et Visualisation Confiance
            def map_action_simple(x):
                if x == 0: return "1"
                elif x == 1: return "N"
                elif x == 2: return "2"
                elif x == 3: return "SKIP"
                return str(x)
            
            def get_conf_color(val):
                if val < 0.5: return "🔴"
                if val < 0.7: return "🟡"
                return "🟢"
                
            df_z_disp = df_zeus_filtered.copy()
            df_z_disp['Action'] = df_z_disp['RawPred'].apply(map_action_simple)
            df_z_disp['Confiance_Visuel'] = df_z_disp['confiance'].apply(get_conf_color) + " " + (df_z_disp['confiance']*100).round(1).astype(str) + "%"
            
            # Affichage Resultat Reel
            def format_resultat(row):
                if pd.isna(row['score_dom']): return "⏳"
                return f"{int(row['score_dom'])} - {int(row['score_ext'])}"
            
            df_z_disp['Resultat'] = df_z_disp.apply(format_resultat, axis=1)
            
            # Outcome Icon
            def outcome_icon(row):
                 if pd.isna(row.get('ZeusSuccess')): return ""
                 return "✅" if row['ZeusSuccess'] == 1 else "❌"
            
            if 'ZeusSuccess' in df_z_disp.columns:
                df_z_disp['Outcome'] = df_z_disp.apply(outcome_icon, axis=1)
            else:
                df_z_disp['Outcome'] = ""

            # Reorder (Sans 'J' car on filtre déjà dessus)
            df_z_disp = df_z_disp[['Domicile', 'Exterieur', 'Action', 'Confiance_Visuel', 'Resultat', 'Outcome']]
            
            st.dataframe(
                df_z_disp,
                use_container_width=True,
                hide_index=True,
                 column_config={
                    "Confiance_Visuel": st.column_config.TextColumn("Confiance"),
                    "Outcome": st.column_config.TextColumn("Succès")
                }
            )
        else:
            st.warning("Aucune donnée Zeus pour l'instant.")

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

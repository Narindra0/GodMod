from src.zeus.env import ZeusEnv

def test_risk_logic():
    print("--- Test Logique Risque & Récompense ---")
    env = ZeusEnv()
    
    # Cas 1: Match Risqué (Cotes serrées)
    match_risky = {
        'score_dom': 1, 'score_ext': 1, # Réalité: Nul
        'cote_1': 2.50, 'cote_x': 3.10, 'cote_2': 2.60 # Serré
    }
    
    is_risky = env.is_risky_match(match_risky)
    print(f"Match Risque (2.50 vs 2.60) détecté comme risqué ? {is_risky}")
    assert is_risky == True
    
    # Test Reward Skip sur Risky
    rew = env._calculate_reward(3, match_risky)
    print(f"Reward Skip sur Risky: {rew} (Attendu: 2)")
    assert rew == 2
    
    # Cas 2: Match Facile (Grand favori)
    match_easy = {
        'score_dom': 2, 'score_ext': 0,
        'cote_1': 1.20, 'cote_x': 6.00, 'cote_2': 12.00 # Fav évident
    }
    
    is_risky_easy = env.is_risky_match(match_easy)
    print(f"Match Facile (1.20) détecté comme risqué ? {is_risky_easy}")
    assert is_risky_easy == False
    
    # Test Reward Skip sur Easy
    rew_easy = env._calculate_reward(3, match_easy)
    print(f"Reward Skip sur Easy: {rew_easy} (Attendu: 0)")
    assert rew_easy == 0
    
    print("✅ Tests Logique Risque PASSÉS")

if __name__ == "__main__":
    test_risk_logic()

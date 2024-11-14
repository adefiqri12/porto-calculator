def calculate_trading_metrics(win_rate, risk_reward_ratios):
    """
    Calculate expected value and other metrics for different risk-reward ratios
    
    Parameters:
    win_rate (float): Probability of winning a trade (0-1)
    risk_reward_ratios (list): List of risk-reward ratios to analyze
    """
    results = []
    
    for rr_ratio in risk_reward_ratios:
        # Assume risk (stop loss) is 1 unit
        risk = 1
        reward = risk * rr_ratio
        
        # Calculate expected value per trade
        expected_value = (win_rate * reward) - ((1 - win_rate) * risk)
        
        # Calculate break-even win rate
        break_even_wr = 1 / (1 + rr_ratio)
        
        results.append({
            'risk_reward_ratio': rr_ratio,
            'expected_value': expected_value,
            'break_even_win_rate': break_even_wr,
            'profit_factor': (win_rate * reward) / ((1 - win_rate) * risk)
        })
    
    return results

# Example calculation with 60% win rate
win_rate = 0.60
risk_reward_ratios = [0.5, 1, 1.5, 2, 2.5, 3]

results = calculate_trading_metrics(win_rate, risk_reward_ratios)

# Print results
print(f"Analysis for {win_rate*100}% Win Rate:\n")
print("R:R Ratio | Exp. Value | Break-Even WR | Profit Factor")
print("-" * 55)
for r in results:
    print(f"{r['risk_reward_ratio']:9.1f} | {r['expected_value']:10.3f} | {r['break_even_win_rate']*100:11.1f}% | {r['profit_factor']:12.2f}")
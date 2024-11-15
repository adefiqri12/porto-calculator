from typing import Dict, Tuple
import sys
import csv
from datetime import datetime

def validate_allocation(allocations: Dict[str, float]) -> bool:
    """Validate if the total allocation equals 100%"""
    total = sum(allocations.values())
    return abs(total - 100) < 0.01  # Using small epsilon for float comparison

def calculate_stock_future_value(
    monthly_investment: float,
    allocation_percentage: float,
    annual_roi: float,
    years: int
) -> float:
    """Calculate future value for a single stock"""
    monthly_rate = (annual_roi / 100) / 12
    total_months = years * 12
    monthly_allocated_investment = monthly_investment * (allocation_percentage / 100)
    
    future_value = monthly_allocated_investment * (
        (pow(1 + monthly_rate, total_months) - 1) / monthly_rate
    ) * (1 + monthly_rate)
    
    return future_value

def portfolio_future_value_calculator():
    """Main function to calculate portfolio future value"""
    try:
        # Get monthly investment and time period
        monthly_investment = float(input("Enter monthly investment amount (Rp): "))
        years = int(input("Enter investment period (years): "))
        
        # Get stock allocations and ROIs
        stocks: Dict[str, Tuple[float, float]] = {}  # {stock_name: (allocation%, annual_roi%)}
        
        while True:
            stock_name = input("\nEnter stock symbol (or 'done' to finish): ").upper()
            if stock_name.lower() == 'done':
                break
                
            allocation = float(input(f"Enter allocation percentage for {stock_name} (%): "))
            annual_roi = float(input(f"Enter expected annual ROI for {stock_name} (%): "))
            
            stocks[stock_name] = (allocation, annual_roi)
            
            # Check total allocation
            current_total = sum(alloc for alloc, _ in stocks.values())
            print(f"\nCurrent total allocation: {current_total}%")
            
            if current_total > 100:
                print("Error: Total allocation exceeds 100%")
                return
            elif current_total == 100:
                break
            else:
                print(f"Remaining allocation: {100 - current_total}%")
        
        # Validate final allocation
        if not validate_allocation({k: v[0] for k, v in stocks.items()}):
            print("Error: Total allocation must equal 100%")
            return
            
        # Calculate future values
        print("\n=== Portfolio Future Value Analysis ===")
        total_future_value = 0
        save_details = input("Would you like to save yearly details? (y/n): ").lower()
        yearly_details = []  # List to store yearly data for CSV if requested
        
        for stock_name, (allocation, annual_roi) in stocks.items():
            future_value = calculate_stock_future_value(
                monthly_investment,
                allocation,
                annual_roi,
                years
            )
            total_future_value += future_value
            
            print(f"\n{stock_name}:")
            print(f"Allocation: {allocation}%")
            print(f"Annual ROI: {annual_roi}%")
            print(f"Future Value: Rp{future_value:,.2f}")
            
            # If yearly details are requested, calculate and save
            if save_details == 'y':
                monthly_rate = (annual_roi / 100) / 12
                total_months = years * 12
                current_value = 0
                yearly_investment = monthly_investment * 12
                
                for year in range(1, years + 1):
                    start_value = current_value
                    cumulative_investment = yearly_investment * year
                    
                    # Calculate end of year value
                    current_value = monthly_investment * (
                        (pow(1 + monthly_rate, year * 12) - 1) / monthly_rate
                    ) * (1 + monthly_rate)
                    
                    # Calculate interest earned this year
                    if year == 1:
                        interest_earned = current_value - yearly_investment
                    else:
                        interest_earned = current_value - start_value - yearly_investment
                    
                    yearly_details.append({
                        'Year': year,
                        'Cumulative_Investment': cumulative_investment,
                        'Interest_Earned': interest_earned,
                        'Total_Value': current_value
                    })
        
        total_invested = monthly_investment * years * 12
        total_profit = total_future_value - total_invested
        
        print("\n=== Summary ===")
        print(f"Total Invested: Rp{total_invested:,.2f}")
        print(f"Total Future Value: Rp{total_future_value:,.2f}")
        print(f"Total Profit: Rp{total_profit:,.2f}")
        print(f"Return Multiple: {total_future_value/total_invested:.2f}x")
        
        # Save yearly details to CSV if requested
        if save_details == 'y':
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"./csv/investment_details_{timestamp}.csv"
            
            # Save to CSV
            with open(filename, 'w', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=[
                    'Year', 
                    'Cumulative_Investment', 
                    'Interest_Earned', 
                    'Total_Value'
                ])
                writer.writeheader()
                for row in yearly_details:
                    writer.writerow({
                        'Year': row['Year'],
                        'Cumulative_Investment': f"{row['Cumulative_Investment']:,.2f}",
                        'Interest_Earned': f"{row['Interest_Earned']:,.2f}",
                        'Total_Value': f"{row['Total_Value']:,.2f}"
                    })
            print(f"\nYearly details have been saved to {filename}")
        
    except ValueError as e:
        print(f"Error: Please enter valid numbers. {str(e)}")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    print("Stock Portfolio Future Value Calculator")
    print("======================================")
    portfolio_future_value_calculator()
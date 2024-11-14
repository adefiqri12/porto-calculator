from typing import Dict, Tuple
import sys

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
        monthly_investment = float(input("Enter monthly investment amount ($): "))
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
            print(f"Future Value: ${future_value:,.2f}")
        
        total_invested = monthly_investment * years * 12
        total_profit = total_future_value - total_invested
        
        print("\n=== Summary ===")
        print(f"Total Invested: ${total_invested:,.2f}")
        print(f"Total Future Value: ${total_future_value:,.2f}")
        print(f"Total Profit: ${total_profit:,.2f}")
        print(f"Return Multiple: {total_future_value/total_invested:.2f}x")
        
    except ValueError as e:
        print(f"Error: Please enter valid numbers. {str(e)}")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    print("Stock Portfolio Future Value Calculator")
    print("======================================")
    portfolio_future_value_calculator()